from typing import TYPE_CHECKING

from schema.category import Category
from schema.field_type import FieldType

if TYPE_CHECKING:
    from schema.data_schema import DataSchema


class FieldSchema:

    def __init__(self, data_schema: 'DataSchema', name: str):
        self.data_schema: 'DataSchema' = data_schema
        self.original_name: str = name
        self.readable_name: str = name
        self.synonyms: dict[str, list[str]] = {'en': []}
        t = self.data_schema.data_source.df[self.original_name].dtype
        if t == 'object':
            t = 'textual'
        if t == 'int64' or t == 'float64':
            t = 'numeric'
        self.type: FieldType = FieldType(t)  # TODO: infer type (datetime, etc)
        self.num_different_values: int = self.data_schema.data_source.df[self.original_name].nunique()
        self.key: bool = False
        self._categorical: bool = self.num_different_values < 10
        self.categories: list[Category] or None = None
        self._update_categories()

        self.tags: list[str] = []

    @property
    def categorical(self):
        return self._categorical

    @categorical.setter
    def categorical(self, value):
        self._categorical = value
        self._update_categories()

    def _update_categories(self):
        if self._categorical and self.categories is None:
            self.categories = []
            for category in self.data_schema.data_source.df[self.original_name].unique():
                self.categories.append(Category(category))

    def get_category(self, value: str):
        if self._categorical and self.categories:
            for category in self.categories:
                if category.value == value:
                    return category
        return None

    def to_dict(self):
        field_schema_dict = {
            'original_name': self.original_name,
            'readable_name': self.readable_name,
            'synonyms': self.synonyms,
            'type': self.type.to_json(),
            'num_different_values': self.num_different_values,
            'key': self.key,
            'categorical': self.categorical,
            'tags': self.tags,
        }
        if self.categorical:
            field_schema_dict['categories'] = [category.to_json() for category in self.categories]
        else:
            field_schema_dict['categories'] = []
        return field_schema_dict