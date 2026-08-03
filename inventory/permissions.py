from stores.permissions import HasPermission


class CanViewInventory(HasPermission):
    required_permission = 'view_inventory'


class CanManageInventory(HasPermission):
    required_permission = 'manage_inventory'