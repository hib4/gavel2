from gavel.models import ma

from gavel.models import Flag


class FlagSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Flag
        load_instance = True
