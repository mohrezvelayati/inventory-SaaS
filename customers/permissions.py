from stores.permissions import HasPermission

class CanManageCustomers(HasPermission):
    required_permission = 'manage_customers'