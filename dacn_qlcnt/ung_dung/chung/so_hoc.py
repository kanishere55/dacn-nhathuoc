from django.db import models


class KhongPhaiNaN(models.Func):
    # Hằng SQL tránh Decimal('NaN') không bằng chính nó gây migration vô hạn.
    template = "(%(expressions)s <> 'NaN'::numeric)"
    arity = 1
    output_field = models.BooleanField()
