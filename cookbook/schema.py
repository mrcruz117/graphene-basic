import graphene
from cookbook.ingredients.schema import Query as IngredientsQuery
from cookbook.ingredients.schema import Mutation as IngredientsMutation


class Query(IngredientsQuery,  graphene.ObjectType):
    pass


class Mutation(IngredientsMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
