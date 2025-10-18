from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction

ROLE_MUDUR = "mudur"
ROLE_PATRON = "patron"
ROLE_PERSONEL = "personel"

class Command(BaseCommand):
    help = "Create or refresh base user roles and assign default permissions"

    @transaction.atomic
    def handle(self, *args, **options):
        groups = {}
        for name in [ROLE_MUDUR, ROLE_PATRON, ROLE_PERSONEL]:
            groups[name], _ = Group.objects.get_or_create(name=name)

        all_perms = Permission.objects.all()
        view_perms = Permission.objects.filter(codename__startswith="view_")

        for g in groups.values():
            g.permissions.clear()

        groups[ROLE_MUDUR].permissions.set(all_perms)
        groups[ROLE_PATRON].permissions.set(view_perms)
        groups[ROLE_PERSONEL].permissions.set(view_perms)

        self.stdout.write(self.style.SUCCESS("Groups and default permissions initialized."))
