TO DO: Update data models to include supply chain sources and outputs (supply tree object)
TO DO: Matching Engine should allow for one to many relationships, not just one to one
TO DO: OME Outputs should be a set of Supply Trees


Spend time tinkering with supply tree object schema
https://github.com/helpfulengineering/project-data-platform/issues/13#issuecomment-1664852954


A SupplyTree should itself be stateless, representing only a possible solution to a problem. There will be a stateful process that actually occurs when a SupplyTree is activated, which is when the actual physical production occurs. 