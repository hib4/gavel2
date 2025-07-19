from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from gavel.models import Decision


class DecisionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Decision
        load_instance = True
