# Leg Workflow
leg_workflow = Workflow(
    name="Chair Leg Manufacturing",
    id=uuid4()
)

leg_nodes = [
    WorkflowNode(
        name="Cut Wood to Length",
        okh_refs=[ResourceURI.from_string("okh://chair-leg/cutting#dimensions")],
        okw_refs=[ResourceURI.from_string("okw://facility-123/equipment/saw")],
        input_requirements={"material": "raw_wood", "length": "45cm"},
        output_specifications={"component": "leg_blank", "length": "45cm"}
    ),
    WorkflowNode(
        name="Turn Leg",
        okh_refs=[ResourceURI.from_string("okh://chair-leg/turning#profile")],
        okw_refs=[ResourceURI.from_string("okw://facility-123/equipment/lathe")],
        input_requirements={"component": "leg_blank"},
        output_specifications={"component": "finished_leg"}
    )
]

# Similar workflows for seat and back...
seat_workflow = Workflow(name="Chair Seat Manufacturing", id=uuid4())
back_workflow = Workflow(name="Chair Back Manufacturing", id=uuid4())

# Assembly workflow
assembly_workflow = Workflow(
    name="Chair Assembly",
    id=uuid4()
)

assembly_nodes = [
    WorkflowNode(
        name="Assemble Base",
        okh_refs=[ResourceURI.from_string("okh://chair/assembly#base")],
        okw_refs=[ResourceURI.from_string("okw://facility-123/capabilities/assembly")],
        input_requirements={
            "components": {
                "seat": 1,
                "legs": 4
            }
        },
        output_specifications={"subassembly": "chair_base"}
    ),
    WorkflowNode(
        name="Attach Back",
        okh_refs=[ResourceURI.from_string("okh://chair/assembly#back")],
        okw_refs=[ResourceURI.from_string("okw://facility-123/capabilities/assembly")],
        input_requirements={
            "subassembly": "chair_base",
            "components": {
                "back": 1
            }
        },
        output_specifications={"product": "finished_chair"}
    )
]

# Create supply tree
chair_supply_tree = SupplyTree()

# Add all workflows
chair_supply_tree.add_workflow(leg_workflow)
chair_supply_tree.add_workflow(seat_workflow)
chair_supply_tree.add_workflow(back_workflow)
chair_supply_tree.add_workflow(assembly_workflow)

# Connect workflows
chair_supply_tree.connect_workflows(
    WorkflowConnection(
        source_workflow=leg_workflow.id,
        source_node=leg_nodes[-1].id,  # Last node of leg workflow
        target_workflow=assembly_workflow.id,
        target_node=assembly_nodes[0].id,  # First assembly node
        connection_type="component",
        metadata={"quantity": 4}  # Specify we need 4 legs
    )
)

# Similar connections for seat and back...