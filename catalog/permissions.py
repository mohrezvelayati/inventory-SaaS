from stores.permissions import HasPermission


class CanManageCatalog(HasPermission):
    required_permission = 'manage_catalog'