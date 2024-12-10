import graphene
from graphene_django import DjangoObjectType
import django_filters

from cookbook.ingredients.models import Category, Ingredient
from django.db.models import QuerySet


class IngredientFilter(django_filters.FilterSet):
    class Meta:
        model = Ingredient
        fields = {
            "name": ["iexact", "icontains"],
            "id": ["exact"],
        }


class IngredientFilterInput(graphene.InputObjectType):
    name = graphene.String()
    name__icontains = graphene.String()
    id = graphene.Int()


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ("id", "name", "ingredients")


class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient
        filterset_class = IngredientFilter
        fields = ("id", "name", "notes", "category")


class IngredientListType(graphene.ObjectType):
    items = graphene.List(IngredientType)
    total_count = graphene.Int()


def apply_filters_and_pagination(queryset: QuerySet, filters: dict, pagination: dict):
    """
    Apply filtering and pagination to a Django queryset.

    :param queryset: The initial queryset.
    :param filters: A dictionary of filters (e.g., {"name__icontains": "salt"}).
    :param pagination: A dictionary with "first" and "offset" keys.
    :return: A filtered and paginated queryset.
    """
    # Apply filters
    if filters:
        queryset = queryset.filter(**filters)

    # Apply pagination
    offset = pagination.get("offset", 0)
    first = pagination.get("first", None)
    if first is not None:
        queryset = queryset[offset: offset + first]
    else:
        queryset = queryset[offset:]

    return queryset


class Query(graphene.ObjectType):
    ingredients = graphene.Field(
        IngredientListType,
        where=graphene.Argument(IngredientFilterInput, required=False),
        first=graphene.Int(),
        offset=graphene.Int(),
    )
    category_by_name = graphene.Field(
        CategoryType, name=graphene.String(required=True))
    total_ingredients = graphene.Int()

    def resolve_ingredients(root, info, where=None, first=None, offset=None):
        ingredients = Ingredient.objects.select_related("category")
        filters = where if where else {}
        pagination = {"first": first, "offset": offset}
        filtered_ingredients = apply_filters_and_pagination(
            ingredients, filters, pagination)
        total_count = filtered_ingredients.count()
        return IngredientListType(items=filtered_ingredients, total_count=total_count)

    def resolve_category_by_name(root, info, name):
        try:
            return Category.objects.get(name=name)
        except Category.DoesNotExist:
            return None

    def resolve_total_ingredients(root, info):
        return Ingredient.objects.count()


schema = graphene.Schema(query=Query)
