from stores.permissions import HasPermission



class CanCreateSale(HasPermission):

    required_permission = 'create_sale'