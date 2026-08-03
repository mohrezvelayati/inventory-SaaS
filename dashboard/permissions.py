from stores.permissions import HasPermission


class CanViewDashboard(HasPermission):
    required_permission = 'view_dashboard'