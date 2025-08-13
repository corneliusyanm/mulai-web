from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from accounts.models import Member
from payments.models import Payment
from visits.models import Visit
from reminders.models import Reminder


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

        # Clean up any malformed reminders before completing
        self.cleanup_malformed_reminders(today, dry_run)

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
                # Resolve if member's active_until was extended beyond the reminder date
                if (
                    reminder.member.active_until
                    and reminder.member.active_until.date() > reminder.due_date
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
        two_weeks_ago = today - timedelta(days=14)

        # Get all installment payments for members who joined at least 14 days ago
        installment_payments = Payment.objects.filter(
            apakah_nyicil=True, member__created_at__date__lte=two_weeks_ago
        ).select_related("member")

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
                        f"Cicilan harus bayar max 3 hari lagi ({next_due.strftime('%d %b %Y')})",
                    ),
                    (
                        next_due,
                        f"Cicilan harus bayar hari ini ({next_due.strftime('%d %b %Y')})",
                    ),
                    (
                        next_due + timedelta(days=3),
                        f"Cicilan belum bayar, sudah lewat 3 hari (seharusnya {next_due.strftime('%d %b %Y')})",
                    ),
                ]

                for reminder_date, reason in reminder_dates:
                    if reminder_date == today:
                        # Check if reminder already exists for this specific date (ignore resolved)
                        existing = Reminder.objects.filter(
                            member=payment.member,
                            reminder_type="PAYMENT_DUE",
                            due_date=reminder_date,
                            is_resolved=False,
                        ).exists()

                        if not existing:
                            if not dry_run:
                                Reminder.objects.create(
                                    member=payment.member,
                                    reminder_type="PAYMENT_DUE",
                                    reason=reason,
                                    due_date=reminder_date,
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
        active_members = Member.objects.filter(active_until__date__gte=today)

        for member in active_members:
            # Get member's last visit
            last_visit = (
                Visit.objects.filter(member=member).order_by("-check_in_time").first()
            )

            # Only create a reminder if a last visit exists and it was exactly 14 days ago
            if last_visit and last_visit.check_in_time.date() == two_weeks_ago:
                # For EXACT date reminders, check if a reminder already exists for this specific date (ignore resolved)
                existing = Reminder.objects.filter(
                    member=member,
                    reminder_type="NO_VISIT",
                    due_date=today,
                    is_resolved=False,
                ).exists()

                if not existing:
                    last_visit_str = last_visit.check_in_time.strftime("%d %b %Y")
                    if not dry_run:
                        Reminder.objects.create(
                            member=member,
                            reminder_type="NO_VISIT",
                            reason=f"Member belum nge-Gym selama 2 minggu. Visit terakhir: {last_visit_str}",
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
        two_weeks_ago = today - timedelta(days=14)

        # Get members with active_until dates who joined at least 14 days ago
        members_with_expiry = Member.objects.filter(
            active_until__isnull=False, created_at__date__lte=two_weeks_ago
        )

        for member in members_with_expiry:
            expiry_date = member.active_until.date()

            # Generate reminders for 3 days before, on day, and 3 days after expiry
            reminder_dates = [
                (
                    expiry_date - timedelta(days=3),
                    f"Membership habis 3 hari lagi ({expiry_date.strftime('%d %b %Y')})",
                ),
                (
                    expiry_date,
                    f"Membership habis hari ini ({expiry_date.strftime('%d %b %Y')})",
                ),
                (
                    expiry_date + timedelta(days=3),
                    f"Membership habis 3 hari lalu (expired {expiry_date.strftime('%d %b %Y')})",
                ),
            ]

            for reminder_date, reason in reminder_dates:
                if reminder_date == today:
                    # Check if reminder already exists for this specific date (ignore resolved)
                    existing = Reminder.objects.filter(
                        member=member,
                        reminder_type="MEMBERSHIP_EXPIRING",
                        due_date=reminder_date,
                        is_resolved=False,
                    ).exists()

                    if not existing:
                        if not dry_run:
                            Reminder.objects.create(
                                member=member,
                                reminder_type="MEMBERSHIP_EXPIRING",
                                reason=reason,
                                due_date=reminder_date,
                            )
                        created_count += 1
                        self.stdout.write(
                            f"  Created expiry reminder: {member.name} - {reason}"
                        )

        self.stdout.write(f"Created {created_count} membership expiry reminders")

    def cleanup_malformed_reminders(self, today, dry_run):
        """Detect and fix malformed reminders with wrong reason text for their due_date"""
        fixed_count = 0

        # Find reminders with mismatched reason and due_date
        malformed_reminders = Reminder.objects.filter(
            reminder_type="MEMBERSHIP_EXPIRING", is_resolved=False
        )

        for reminder in malformed_reminders:
            needs_fix = False
            correct_reason = None

            # Check if reason doesn't match due_date
            if reminder.due_date == today and "3 hari lagi" in reminder.reason:
                # Should be "hari ini" not "3 hari lagi"
                expiry_date = (
                    reminder.due_date
                )  # In this case, due_date is the expiry date
                correct_reason = (
                    f"Membership habis hari ini ({expiry_date.strftime('%d %b %Y')})"
                )
                needs_fix = True
            elif reminder.due_date == today and "3 hari lalu" in reminder.reason:
                # Should be "hari ini" not "3 hari lalu"
                expiry_date = reminder.due_date
                correct_reason = (
                    f"Membership habis hari ini ({expiry_date.strftime('%d %b %Y')})"
                )
                needs_fix = True

            if needs_fix:
                if not dry_run:
                    reminder.reason = correct_reason
                    reminder.save()
                fixed_count += 1
                self.stdout.write(
                    f"  Fixed malformed reminder: {reminder.member.name} - {correct_reason}"
                )

        if fixed_count > 0:
            self.stdout.write(f"Fixed {fixed_count} malformed reminders")
