import coreapi
import coreschema
from rest_framework.schemas import AutoSchema


class KeyValueSchema(AutoSchema):
    def get_manual_fields(self, path, method):
        """Example adding per-method fields."""

        extra_fields = [
            coreapi.Field(
                name="id",
                required=True,
                location='path',
                schema=coreschema.String(
                    title="Key data"
                ),
            ),
        ]
        if method == 'PUT':
            extra_fields += [
                coreapi.Field(
                    name="value",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Value",
                    ),
                ),
            ]

        manual_fields = super().get_manual_fields(path, method)
        return manual_fields + extra_fields