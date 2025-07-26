from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from accounts.models import Member
from payments.models import Payment
from visits.models import Visit, Reminder


class Command(BaseCommand):
    help = "Generate daily reminders for members and auto-resolve completed ones"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without making changes to see what would be created/resolved",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Auto-resolve reminders first
        self.auto_resolve_reminders(today, dry_run)

        # Generate new reminders
        self.generate_payment_reminders(today, dry_run)
        self.generate_no_visit_reminders(today, dry_run)
        self.generate_membership_expiry_reminders(today, dry_run)

        self.stdout.write(self.style.SUCCESS("Reminder generation completed"))

    def auto_resolve_reminders(self, today, dry_run):
        """Auto-resolve reminders when conditions are no longer met"""
        resolved_count = 0

        # Get all active reminders
        active_reminders = Reminder.objects.filter(is_resolved=False)

        for reminder in active_reminders:
            should_resolve = False

            if reminder.reminder_type == "PAYMENT_DUE":
                # Resolve if member made a new payment after the reminder was created
                new_payments = Payment.objects.filter(
                    member=reminder.member,
                    apakah_nyicil=True,
                    payment_date__date__gte=reminder.created_date.date(),
                )
                if new_payments.exists():
                    should_resolve = True

            elif reminder.reminder_type == "NO_VISIT":
                # Resolve if member visited after the reminder was created
                new_visits = Visit.objects.filter(
                    member=reminder.member,
                    check_in_time__date__gte=reminder.created_date.date(),
                )
                if new_visits.exists():
                    should_resolve = True

            elif reminder.reminder_type == "MEMBERSHIP_EXPIRING":
                # Resolve if member's active_until was extended after reminder
                if (
                    reminder.member.active_until
                    and reminder.member.active_until.date()
                    > reminder.due_date + timedelta(days=3)
                ):
                    should_resolve = True

            if should_resolve:
                if not dry_run:
                    reminder.mark_resolved()
                resolved_count += 1
                self.stdout.write(
                    f"  Auto-resolved: {reminder.member.name} - {reminder.get_reminder_type_display()}"
                )

        self.stdout.write(f"Auto-resolved {resolved_count} reminders")

    def generate_payment_reminders(self, today, dry_run):
        """Generate reminders for installment payments (apakah_nyicil=True)"""
        created_count = 0

        # Get all installment payments
        installment_payments = Payment.objects.filter(apakah_nyicil=True)

        for payment in installment_payments:
            payment_date = payment.payment_date.date()

            # Calculate next due dates (monthly)
            months_passed = 1
            while True:
                next_due = payment_date + relativedelta(months=months_passed)

                # Stop if next due is more than 3 days in the future
                if next_due > today + timedelta(days=3):
                    break

                # Check if we should create reminders for this due date
                reminder_dates = [
                    (
                        next_due - timedelta(days=3),
                        f"Payment due in 3 days ({next_due.strftime('%d %b %Y')})",
                    ),
                    (next_due, f"Payment due today ({next_due.strftime('%d %b %Y')})"),
                    (
                        next_due + timedelta(days=3),
                        f"Payment overdue by 3 days (was due {next_due.strftime('%d %b %Y')})",
                    ),
                ]

                for reminder_date, reason in reminder_dates:
                    if reminder_date == today:
                        # Check if reminder already exists (with new constraint)
                        existing = Reminder.objects.filter(
                            member=payment.member,
                            reminder_type="PAYMENT_DUE",
                            due_date=next_due,
                        ).exists()

                        if not existing:
                            if not dry_run:
                                Reminder.objects.create(
                                    member=payment.member,
                                    reminder_type="PAYMENT_DUE",
                                    reason=f"Installment payment: {reason}",
                                    due_date=next_due,
                                )
                            created_count += 1
                            self.stdout.write(
                                f"  Created payment reminder: {payment.member.name} - {reason}"
                            )

                months_passed += 1

        self.stdout.write(f"Created {created_count} payment reminders")

    def generate_no_visit_reminders(self, today, dry_run):
        """Generate reminders for members whose last visit was exactly 14 days ago"""
        created_count = 0
        two_weeks_ago = today - timedelta(days=14)

        # Get all active members
        active_members = Member.objects.filter(
            Q(active_until__isnull=True) | Q(active_until__date__gte=today)
        )

        for member in active_members:
            # Get member's last visit
            last_visit = (
                Visit.objects.filter(member=member).order_by("-check_in_time").first()
            )

            # Check if member's last visit was EXACTLY 14 days ago (or never visited)
            should_create_reminder = False
            if not last_visit:
                # Never visited - create reminder once (check if not already exists)
                should_create_reminder = not Reminder.objects.filter(
                    member=member, reminder_type="NO_VISIT", is_resolved=False
                ).exists()
            elif last_visit.check_in_time.date() == two_weeks_ago:
                # Last visit was exactly 14 days ago - create reminder
                should_create_reminder = True

            if should_create_reminder:
                # For EXACT date reminders, check if reminder already exists for this specific date
                existing = Reminder.objects.filter(
                    member=member, reminder_type="NO_VISIT", due_date=today
                ).exists()

                if not existing:
                    last_visit_str = (
                        last_visit.check_in_time.strftime("%d %b %Y")
                        if last_visit
                        else "Never"
                    )
                    if not dry_run:
                        Reminder.objects.create(
                            member=member,
                            reminder_type="NO_VISIT",
                            reason=f"Member hasn't visited the gym in 14 days. Last visit: {last_visit_str}",
                            due_date=today,
                        )
                    created_count += 1
                    self.stdout.write(
                        f"  Created no-visit reminder: {member.name} - Last visit: {last_visit_str}"
                    )

        self.stdout.write(f"Created {created_count} no-visit reminders")

    def generate_membership_expiry_reminders(self, today, dry_run):
        """Generate reminders for memberships expiring soon"""
        created_count = 0

        # Get members with active_until dates
        members_with_expiry = Member.objects.filter(active_until__isnull=False)

        for member in members_with_expiry:
            expiry_date = member.active_until.date()

            # Generate reminders for 3 days before, on day, and 3 days after expiry
            reminder_dates = [
                (
                    expiry_date - timedelta(days=3),
                    f"Membership expires in 3 days ({expiry_date.strftime('%d %b %Y')})",
                ),
                (
                    expiry_date,
                    f"Membership expires today ({expiry_date.strftime('%d %b %Y')})",
                ),
                (
                    expiry_date + timedelta(days=3),
                    f"Membership expired 3 days ago (expired {expiry_date.strftime('%d %b %Y')})",
                ),
            ]

            for reminder_date, reason in reminder_dates:
                if reminder_date == today:
                    # Check if reminder already exists (with new constraint)
                    existing = Reminder.objects.filter(
                        member=member,
                        reminder_type="MEMBERSHIP_EXPIRING",
                        due_date=expiry_date,
                    ).exists()

                    if not existing:
                        if not dry_run:
                            Reminder.objects.create(
                                member=member,
                                reminder_type="MEMBERSHIP_EXPIRING",
                                reason=reason,
                                due_date=expiry_date,
                            )
                        created_count += 1
                        self.stdout.write(
                            f"  Created expiry reminder: {member.name} - {reason}"
                        )

        self.stdout.write(f"Created {created_count} membership expiry reminders")
