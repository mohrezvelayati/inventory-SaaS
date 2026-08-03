from stores.permissions import HasPermission

class CanManageWanted(HasPermission):
    required_permission = 'manage_wanted'