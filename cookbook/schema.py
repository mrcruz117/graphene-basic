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
    ingredients = graphene.Field(IngredientListType)
    category_by_name = graphene.Field(
        CategoryType, name=graphene.String(required=True))
    total_ingredients = graphene.Int()

    def resolve_ingredients(root, info, first=None, offset=None):
        ingredients = Ingredient.objects.select_related("category").all()

        if offset:
            ingredients = ingredients[offset:]
        if first:
            ingredients = ingredients[:first]

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
