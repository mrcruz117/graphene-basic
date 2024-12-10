import graphene
from graphene_django import DjangoObjectType

from cookbook.ingredients.models import Category, Ingredient


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
    ingredients = graphene.Field(IngredientListType,
                                 first=graphene.Int(),
                                 offset=graphene.Int(),)
    category_by_name = graphene.Field(
        CategoryType, name=graphene.String(required=True))
    total_ingredients = graphene.Int()

    def resolve_ingredients(root, info, first=None, offset=None):
        ingredients = Ingredient.objects.select_related("category")
        if offset is None:
            offset = 0
        if first is not None:
            ingredients = ingredients[offset : offset + first]
        else:
            ingredients = ingredients[offset:]
        total_count = ingredients.count()
        return IngredientListType(items=ingredients, total_count=total_count)

    def resolve_category_by_name(root, info, name):
        try:
            return Category.objects.get(name=name)
        except Category.DoesNotExist:
            return None

    def resolve_total_ingredients(root, info):
        return Ingredient.objects.count()


schema = graphene.Schema(query=Query)
