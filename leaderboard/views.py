"""The member-facing leaderboard.

Members only. The board is a list of real people and how often they train, so it
stays behind the member session rather than being readable by anyone who finds
the URL.
"""

from accounts.views import MemberRequiredMixin
from django.views.generic import TemplateView

from accounts.models import Member

from . import board as board_module


class LeaderboardView(MemberRequiredMixin, TemplateView):
    template_name = "leaderboard/board.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = Member.objects.filter(
            email=self.request.session.get("member_email")
        ).first()

        period = board_module.resolve_period(self.request.GET.get("periode"))
        context["member"] = member
        context["board"] = board_module.board(period, member=member)
        context["period"] = period
        context["months"] = board_module.months_available()
        context["lifetime"] = board_module.lifetime_period()
        context["points"] = board_module.POINTS
        return context
