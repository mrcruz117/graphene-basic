import graphene
from graphene_django import DjangoObjectType


from cookbook.ingredients.models import Category, Ingredient
from django.db.models import QuerySet


class IngredientWhereInput(graphene.InputObjectType):
    name_contains = graphene.String()
    category_id = graphene.Int()
    notes_contains = graphene.String()


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ("id", "name", "ingredients")


class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient
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
        where=IngredientWhereInput(),
        first=graphene.Int(),
        offset=graphene.Int(),
    )
    category_by_name = graphene.Field(
        CategoryType, name=graphene.String(required=True))
    total_ingredients = graphene.Int()

    def resolve_ingredients(root, info, where=None, first=None, offset=None):
        ingredients = Ingredient.objects.select_related("category")

        # Convert "where" object into a Django filter dictionary
        filters = {}
        if where:
            if where.name_contains:
                filters["name__icontains"] = where.name_contains
            if where.category_id:
                filters["category_id"] = where.category_id
            if where.notes_contains:
                filters["notes__icontains"] = where.notes_contains

        # Apply filters and pagination
        pagination = {"first": first, "offset": offset or 0}
        filtered_ingredients = apply_filters_and_pagination(
            ingredients, filters, pagination)

        # Return the result
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
