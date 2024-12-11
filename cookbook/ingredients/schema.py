import graphene
from graphql import GraphQLError
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


class IngredientOrderField(graphene.Enum):
    name = "name"
    id = "id"


class OrderDirection(graphene.Enum):
    ASC = "ASC"
    DESC = "DESC"


class IngredientOrderInput(graphene.InputObjectType):
    field = graphene.Argument(IngredientOrderField, required=True)
    direction = graphene.Argument(OrderDirection, required=True)


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


class IngredientQuery(graphene.ObjectType):
    ingredients = graphene.Field(
        IngredientListType,
        where=graphene.Argument(IngredientFilterInput, required=False),
        first=graphene.Int(),
        offset=graphene.Int(),
        order=graphene.Argument(IngredientOrderInput, required=False),
    )

    def resolve_ingredients(root, info, where=None, first=None, offset=None, order=None):
        # Start with the base queryset
        ingredients = Ingredient.objects.select_related("category")

        # Apply filters using IngredientFilter
        if where:
            filter_data = {key: value for key,
                           value in where.items() if value is not None}
            filtered_qs = IngredientFilter(
                filter_data, queryset=ingredients).qs
        else:
            filtered_qs = ingredients

        # Apply ordering
        if order:
            direction = '-' if order.direction == OrderDirection.DESC else ''
            filtered_qs = filtered_qs.order_by(
                f"{direction}{order.field.value}")

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


class CategoryQuery(graphene.ObjectType):
    category_by_name = graphene.Field(
        CategoryType,
        name=graphene.String(required=True),
    )

    def resolve_category_by_name(root, info, name):
        try:
            return Category.objects.get(name=name)
        except Category.DoesNotExist:
            return None


class StatsQuery(graphene.ObjectType):
    total_ingredients = graphene.Int()

    def resolve_total_ingredients(root, info):
        return Ingredient.objects.count()


class UpsertIngredientInput(graphene.InputObjectType):
    id = graphene.ID()   # ID is optional
    name = graphene.String(required=True)
    notes = graphene.String()
    category_name = graphene.String(required=True)


# Ingredient Type for Response
class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient


class UpsertIngredient(graphene.Mutation):
    class Arguments:
        input = UpsertIngredientInput(required=True)

    ingredient = graphene.Field(IngredientType)

    def mutate(self, info, input):
        ingredient_id = input.get("id")
        name = input.get("name")
        notes = input.get("notes")
        category_name = input.get("category_name")

        # Ensure the category exists
        try:
            category, _ = Category.objects.get_or_create(name=category_name)
        except Exception as e:
            raise GraphQLError(
                f"Error creating or retrieving category: {str(e)}")

        # If id is provided, attempt to update the existing ingredient
        if ingredient_id:
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
                ingredient.name = name
                ingredient.notes = notes
                ingredient.category = category
                ingredient.save()
            except Ingredient.DoesNotExist:
                raise GraphQLError(f"Ingredient with id {
                                   ingredient_id} does not exist.")
        else:
            # Create a new ingredient
            ingredient = Ingredient.objects.create(
                name=name,
                notes=notes,
                category=category,
            )

        return UpsertIngredient(ingredient=ingredient)


class Mutation(UpsertIngredient, graphene.ObjectType):
    # upsert_ingredient = UpsertIngredient.Field()
    pass


class Query(IngredientQuery, CategoryQuery, StatsQuery, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
