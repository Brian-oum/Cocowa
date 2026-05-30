from .models import (
    IndividualMember,
    SaccoMember,
    PartnerMember
)

def member_context(request):

    if not request.user.is_authenticated:
        return {}

    profile = getattr(request.user, "userprofile", None)

    if not profile:
        return {}

    member = None

    # =========================
    # INDIVIDUAL
    # =========================
    if profile.role == "individual":
        member = IndividualMember.objects.filter(user=request.user).first()

    # =========================
    # SACCO
    # =========================
    elif profile.role == "sacco":
        member = SaccoMember.objects.filter(user=request.user).first()

    # =========================
    # PARTNER
    # =========================
    elif profile.role == "partner":
        member = PartnerMember.objects.filter(user=request.user).first()

    return {
        "member": member,
        "user_role": profile.role if profile else None
    }