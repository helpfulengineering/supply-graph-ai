/** Cooking-domain kitchen, mirroring src/core/domains/cooking/models.py KitchenCapability. */

export interface Kitchen {
  id: string;
  name: string;
  appliances: string[];
  tools: string[];
  ingredients: string[];
  domain: "cooking";
}
