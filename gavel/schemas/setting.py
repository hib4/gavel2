from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from gavel.models.setting import Setting


class SettingSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Setting
        load_instance = True
