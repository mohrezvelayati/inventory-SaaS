from stores.permissions import HasPermission


class CanViewInventory(HasPermission):
    required_permission = 'view_inventory'