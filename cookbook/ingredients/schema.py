import graphene
from graphql import GraphQLError
from graphene_django import DjangoObjectType
import django_filters
from django.core.exceptions import FieldError
from cookbook.ingredients.models import Category, Ingredient

# Helper function for filtering


def apply_filters(queryset, filter_data):
    """
    Applies filtering to a queryset based on the provided filter data.
    """
    if filter_data:
        try:
            return queryset.filter(**filter_data)
        except FieldError as e:
            raise GraphQLError(f"Invalid filter: {str(e)}")
    return queryset

# Helper function for ordering


def apply_ordering(queryset, order_input):
    """
    Applies ordering to a queryset based on the provided order input.
    """
    if order_input:
        direction = '-' if order_input.direction == OrderDirection.DESC else ''
        return queryset.order_by(f"{direction}{order_input.field.value}")
    return queryset

# Helper function for pagination


def apply_pagination(queryset, first=None, offset=None):
    """
    Applies pagination to a queryset based on the provided first and offset values.
    """
    offset = offset or 0
    if first is not None:
        return queryset[offset: offset + first]
    return queryset[offset:]


def update_fields(instance, fields):
    """
    Update an instance's attributes with the provided fields.

    :param instance: The model instance to update.
    :param fields: A dictionary of fields and their new values.
    """
    for field, value in fields.items():
        if value is not None:
            setattr(instance, field, value)

# Ingredient Filter Type


class IngredientFilterInput(graphene.InputObjectType):
    name__iexact = graphene.String()
    name__icontains = graphene.String()
    id = graphene.Int()

# Ingredient Order Types


class IngredientOrderField(graphene.Enum):
    name = "name"
    id = "id"


class OrderDirection(graphene.Enum):
    ASC = "ASC"
    DESC = "DESC"


class IngredientOrderInput(graphene.InputObjectType):
    field = graphene.Argument(IngredientOrderField, required=True)
    direction = graphene.Argument(OrderDirection, required=True)

# GraphQL Types


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

# Queries


class IngredientQuery(graphene.ObjectType):
    ingredients = graphene.Field(
        IngredientListType,
        where=graphene.Argument(IngredientFilterInput, required=False),
        first=graphene.Int(),
        offset=graphene.Int(),
        order=graphene.Argument(IngredientOrderInput, required=False),
    )

    ingredient = graphene.Field(IngredientType, id=graphene.ID(required=True))

    def resolve_ingredient(root, info, id):
        try:
            return Ingredient.objects.get(id=id)
        except Ingredient.DoesNotExist:
            raise GraphQLError(f"Ingredient with id {id} does not exist.")

    def resolve_ingredients(root, info, where=None, first=None, offset=None, order=None):
        # Start with the base queryset
        queryset = Ingredient.objects.select_related("category")

        # Apply filters
        filter_data = {key: value for key, value in (
            where or {}).items() if value is not None}
        filtered_qs = apply_filters(queryset, filter_data)

        # Apply ordering
        ordered_qs = apply_ordering(filtered_qs, order)

        # Get total count after filtering
        total_count = ordered_qs.count()

        # Apply pagination
        paginated_qs = apply_pagination(ordered_qs, first=first, offset=offset)

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

# Mutations


class UpsertIngredientInput(graphene.InputObjectType):
    id = graphene.ID()   # ID is optional
    name = graphene.String()
    notes = graphene.String()
    category_name = graphene.String()


class UpsertIngredient(graphene.Mutation):
    class Arguments:
        input = UpsertIngredientInput(required=True)

    ingredient = graphene.Field(IngredientType)

    def mutate(self, info, input):
        ingredient_id = input.get("id")
        name = input.get("name")
        notes = input.get("notes")
        category_name = input.get("category_name")

        # If ID is not provided, ensure name and category_name are provided
        if not ingredient_id:
            if not name:
                raise GraphQLError(
                    "Name is required when creating a new ingredient.")
            if not category_name:
                raise GraphQLError(
                    "Category name is required when creating a new ingredient.")

        # Ensure the category exists
        category = None
        if category_name:
            try:
                category, _ = Category.objects.get_or_create(
                    name=category_name)
            except Exception as e:
                raise GraphQLError(
                    f"Error creating or retrieving category: {str(e)}")

        # Check for duplicate name if the name is being updated or if creating a new ingredient
        if name and Ingredient.objects.filter(name=name).exclude(id=ingredient_id).exists():
            raise GraphQLError(f"Ingredient with name '{
                               name}' already exists.")

        # If ID is provided, update the existing ingredient
        if ingredient_id:
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
                # Update fields dynamically
                update_fields(ingredient, {
                    "name": name,
                    "notes": notes,
                    "category": category,
                })
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


class DeleteIngredient(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, id):
        try:
            ingredient = Ingredient.objects.get(id=id)
            ingredient.delete()
            return DeleteIngredient(success=True)
        except Ingredient.DoesNotExist:
            raise GraphQLError(f"Ingredient with id {id} does not exist.")


class Mutation(graphene.ObjectType):
    upsert_ingredient = UpsertIngredient.Field()
    delete_ingredient = DeleteIngredient.Field()


class Query(IngredientQuery, CategoryQuery, StatsQuery, graphene.ObjectType):
    pass
