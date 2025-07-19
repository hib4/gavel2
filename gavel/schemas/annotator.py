from gavel.models import ma

from gavel.models import Annotator


class AnnotatorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Annotator
        load_instance = True
