from stores.permissions import HasPermission



class CanCreateSale(HasPermission):
    required_permission = 'create_sale'


class CanViewSales(HasPermission):
    required_permission = 'view_sales'