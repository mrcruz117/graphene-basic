import graphene
from graphene_django import DjangoObjectType
import django_filters
from cookbook.ingredients.models import Category, Ingredient


class IngredientFilter(django_filters.FilterSet):
    class Meta:
        model = Ingredient
        fields = {
            "name": ["iexact", "icontains"],
            "id": ["exact"],
        }


class IngredientFilterInput(graphene.InputObjectType):
    name__iexact = graphene.String()
    name__icontains = graphene.String()
    id = graphene.Int()


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


class Query(graphene.ObjectType):
    ingredients = graphene.Field(
        IngredientListType,
        where=graphene.Argument(IngredientFilterInput, required=False),
        first=graphene.Int(),
        offset=graphene.Int(),
    )
    category_by_name = graphene.Field(
        CategoryType, name=graphene.String(required=True)
    )
    total_ingredients = graphene.Int()

    def resolve_ingredients(root, info, where=None, first=None, offset=None):
        # Start with the base queryset
        ingredients = Ingredient.objects.select_related("category")

        # Apply filters using IngredientFilter
        if where:
            filter_data = {key: value for key, value in where.items() if value is not None}
            filtered_qs = IngredientFilter(filter_data, queryset=ingredients).qs
        else:
            filtered_qs = ingredients

        # Apply pagination
        offset = offset or 0
        if first is not None:
            paginated_qs = filtered_qs[offset: offset + first]
        else:
            paginated_qs = filtered_qs[offset:]

        # Total count of filtered ingredients
        total_count = filtered_qs.count()

        # Return the result
        return IngredientListType(items=paginated_qs, total_count=total_count)
    
    def resolve_category_by_name(root, info, name):
        try:
            return Category.objects.get(name=name)
        except Category.DoesNotExist:
            return None

    def resolve_total_ingredients(root, info):
        return Ingredient.objects.count()


schema = graphene.Schema(query=Query)
