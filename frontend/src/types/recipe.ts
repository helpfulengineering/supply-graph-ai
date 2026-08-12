/** Cooking-domain recipe, mirroring src/core/domains/cooking/models.py Recipe. */

export interface Recipe {
  id: string;
  name: string;
  ingredients: string[];
  instructions: string[];
  equipment: string[];
  domain: "cooking";
}
