# OHM Demo Script - Multi-Facility Matching

**Total Time**: 10 minutes  
**Date**: January 2025  
**Status**: Draft Outline

---

## Overview

This script demonstrates how Open Hardware Manager (OHM) solves the multi-facility coordination problem for complex hardware designs. The demo shows the complete workflow from design selection to RFQ generation, highlighting how OHM enables small-batch, local, urgent production through intelligent facility matching.

**Key Message**: OHM makes it possible to find and coordinate multiple specialized facilities to produce complex hardware designs that no single facility can complete alone.

---

## Pre-Demo Checklist

**Before Starting**:
- [ ] Verify API is accessible (run `python demo/infrastructure/run_pre_demo_check.py`)
- [ ] Confirm demo data is loaded (10 OKH + 34 OKW facilities)
- [ ] Test internet connection
- [ ] Have backup deployment ready (if needed)
- [ ] Close unnecessary applications
- [ ] Full-screen browser window
- [ ] Test microphone/audio (if recording)

**Demo Environment**:
- Streamlit app running: `streamlit run demo/app.py`
- Browser: Full-screen mode
- Screen: Large monitor or projector (tested for visibility)

---

## Section 1: Setup & Introduction (1 minute)

### 1.1 Opening (15 seconds)

**Action**: Show Streamlit app title screen

**Script**:
> "Today I'm going to show you Open Hardware Manager, or OHM - a system that solves a critical problem in distributed hardware manufacturing. Let me start by showing you what we're working with."

**Visual**: App title "🔧 OHM Demo - Multi-Facility Matching"

---

### 1.2 Map Overview (30 seconds)

**Action**: Point to map showing facilities

**Script**:
> "Here we have a map showing 34 manufacturing facilities across the United States. Each red pin represents a facility with specific capabilities - 3D printing, PCB fabrication, electronics assembly, and more. These are real facilities that could be part of a distributed manufacturing network."

**Key Points**:
- 34 facilities visible on map
- Geographic distribution
- Specialized capabilities
- Real-world scenario

**Visual**: Map with facility pins visible

---

### 1.3 Problem Statement (15 seconds)

**Action**: Transition to problem

**Script**:
> "But here's the challenge: when you need to produce a complex hardware design, no single facility can do it all. You need to coordinate multiple facilities, each handling different components. That's what OHM solves."

**Transition**: Move to Design Selection section

---

## Section 2: The Problem (2 minutes)

### 2.1 Complex Design Example (45 seconds)

**Action**: Show OKH design selection dropdown

**Script**:
> "Let's say you need to produce this: a 3D Printed Prosthetic Hand. This isn't just one part - it's a complex assembly with multiple components: sensor PCBs, microcontrollers, 3D printed enclosures, and final assembly. Each component requires different manufacturing capabilities."

**Action**: Select "3D Printed Prosthetic Hand" from dropdown

**Visual**: Design details showing:
- Complexity: Medium/Complex
- Components: Multiple (shows count)
- Description visible

**Key Points**:
- Complex designs have multiple components
- Each component needs different capabilities
- No single facility can do everything

---

### 2.2 The Coordination Challenge (45 seconds)

**Action**: Explain the problem without showing solution yet

**Script**:
> "The traditional approach would be: find a facility that can do everything, or manually coordinate multiple facilities yourself. But here's the reality: specialized facilities exist - a 3D printing shop here, a PCB fab there, an assembly facility somewhere else. Manually finding and coordinating them is time-consuming, error-prone, and doesn't scale."

**Key Points**:
- Manual coordination is hard
- Specialized facilities exist but are scattered
- Need to match capabilities to requirements
- Time-sensitive for urgent production

**Visual**: Still on design selection, haven't run matching yet

---

### 2.3 The Question (30 seconds)

**Action**: Set up the solution

**Script**:
> "So the question is: How do you quickly find the right combination of facilities that can collectively produce your design? And how do you know they can actually work together? That's where OHM comes in."

**Transition**: "Let me show you how OHM solves this..."

---

## Section 3: The Solution (4 minutes)

### 3.1 Matching Execution (1 minute)

**Action**: 
1. Set quantity (e.g., 10 units)
2. Click "Match Facilities" button
3. Show spinner/loading

**Script**:
> "OHM uses intelligent matching to find facilities that can produce your design. I'll set the quantity to 10 units - this is a small batch, which is common for urgent or prototype production. Now I'll run the matching algorithm."

**Action**: Click "Match Facilities"

**Script** (while loading):
> "The system is analyzing the design requirements, matching them against facility capabilities using multiple techniques: direct matching for exact capabilities, heuristic rules for related processes, and NLP for semantic understanding. This takes about 30-60 seconds for complex designs."

**Key Points**:
- Multi-layered matching (direct, heuristic, NLP, LLM)
- Handles small batch quantities
- Works for urgent production needs
- Analyzes all components

**Visual**: Loading spinner, then success message

---

### 3.2 Results Overview (1 minute)

**Action**: Show matching results summary

**Script**:
> "Perfect! OHM found a solution. This design requires 12 facilities working together - no single facility can produce the entire design. The system identified that we need PCB fabrication facilities, 3D printing facilities, and assembly facilities, each handling specific components."

**Visual**: Results section showing:
- "Multi-Facility Solution Detected"
- Facility count
- Solution summary

**Key Points**:
- Multi-facility coordination required
- Each facility is specialized
- System identified the right combination
- All components covered

---

### 3.3 Production Plan (1.5 minutes)

**Action**: Expand Production Plan section, show component-centric view

**Script**:
> "Let's look at the Production Plan. OHM organizes this by component - so you can see exactly which facilities can produce each part. For example, for the 'Sensor PCB' component, we have 3 facilities available, each in different locations. This is crucial for local production - you can choose facilities near you."

**Action**: Expand one component (e.g., "Sensor PCB")

**Visual**: Show:
- Component name
- Multiple facilities listed
- Location (city, country) for each
- Confidence scores

**Script** (while showing locations):
> "Notice each facility shows its location - Philadelphia, Dallas, New York. For urgent, local production, you can choose facilities closest to you. The system shows confidence scores so you know the quality of each match."

**Key Points**:
- Component-centric organization
- Location information for local decisions
- Multiple options per component
- Confidence scores for quality assessment

**Action**: Expand another component (e.g., "3D Printed Enclosure")

**Script**:
> "For the 3D Printed Enclosure, we have 6 facilities available. This gives you flexibility - you can choose based on location, capacity, or lead time. The system shows you all the options."

---

### 3.4 Facility Details (30 seconds)

**Action**: Go back to map, select a facility from dropdown

**Script**:
> "You can click on any facility to see detailed information. Let me show you one of the 3D printing facilities."

**Action**: Select facility from dropdown, show details

**Visual**: Facility details showing:
- Name, location, contact
- Manufacturing processes
- Equipment list (with make/model)
- Status

**Script**:
> "Here you can see the facility's capabilities, equipment, and contact information. This helps you make informed decisions about which facilities to work with."

**Key Points**:
- Detailed facility information
- Equipment specifications
- Contact information
- Manufacturing processes

---

### 3.5 RFQ Generation (1 minute)

**Action**: Scroll to RFQ Generation section, click "Generate RFQs"

**Script**:
> "Once you've reviewed the matches, OHM can generate Request for Quotation documents for each facility. This automates what would normally be a manual, time-consuming process."

**Action**: Click "Generate RFQs" button

**Script** (while generating):
> "The system is creating professional RFQ documents for each facility, including design specifications, manufacturing requirements, and quantity information."

**Action**: Show generated RFQ

**Visual**: Expand first RFQ, show RFQ text

**Script**:
> "Here's an example RFQ for one of the facilities. It includes all the necessary information: design details, manufacturing processes required, materials needed, and quantity. You can copy this and send it directly to the facility."

**Key Points**:
- Automated RFQ generation
- Professional format
- Includes all necessary information
- Ready to send to facilities

**Action**: Show RFQ includes:
- Design name (correctly extracted)
- Facility information
- Manufacturing requirements
- Quantity

---

## Section 4: Impact & Value (2 minutes)

### 4.1 Time Savings (30 seconds)

**Script**:
> "What would have taken hours or days of manual research and coordination, OHM does in under a minute. For urgent production needs, this speed is critical."

**Key Points**:
- Minutes vs. hours/days
- Critical for urgent production
- Reduces manual work

---

### 4.2 Local Production Enablement (30 seconds)

**Script**:
> "OHM makes local production feasible. By showing you facilities with their locations, you can choose facilities near you, reducing shipping time and costs. This is especially valuable for small-batch, urgent production."

**Action**: Point to location information in Production Plan

**Key Points**:
- Location-based selection
- Reduces shipping time
- Lower costs
- Better for small batches

---

### 4.3 Scalability (30 seconds)

**Script**:
> "This isn't just for one design. OHM can handle any OKH design - medical devices, IoT sensors, open-source hardware. The system scales to handle complex designs with dozens of components and hundreds of facilities."

**Key Points**:
- Works for any OKH design
- Handles complex designs
- Scales to many facilities
- General-purpose solution

---

### 4.4 Real-World Application (30 seconds)

**Script**:
> "This solves a real problem in distributed manufacturing. Whether you're a startup needing prototype production, a maker space coordinating community projects, or a manufacturer looking for specialized capabilities, OHM makes multi-facility coordination practical and efficient."

**Key Points**:
- Real-world problem
- Multiple use cases
- Practical solution
- Enables new workflows

---

## Section 5: Wrap-Up (1 minute)

### 5.1 Key Takeaways (30 seconds)

**Script**:
> "To summarize: OHM solves the multi-facility coordination problem by automatically matching design requirements to facility capabilities, organizing results by component for easy decision-making, and generating RFQs to streamline the procurement process."

**Key Points**:
- Automatic matching
- Component-centric organization
- RFQ generation
- End-to-end workflow

---

### 5.2 Next Steps (20 seconds)

**Script**:
> "This is a working demonstration of the core matching and coordination capabilities. The system is designed to integrate with existing manufacturing workflows and can be extended with additional features like cost estimation, lead time prediction, and automated ordering."

**Key Points**:
- Working demonstration
- Integration-ready
- Extensible
- Future capabilities

---

### 5.3 Closing (10 seconds)

**Script**:
> "Thank you. I'm happy to answer any questions about how OHM works or how it could be applied to your use case."

**Action**: Be ready for questions

---

## Timing Breakdown

| Section | Target Time | Buffer | Notes |
|---------|-------------|--------|-------|
| 1. Setup & Introduction | 1:00 | +0:10 | Map overview is key |
| 2. The Problem | 2:00 | +0:15 | Don't rush problem statement |
| 3. The Solution | 4:00 | +0:30 | Longest section, most important |
| 4. Impact & Value | 2:00 | +0:15 | Keep concise |
| 5. Wrap-Up | 1:00 | +0:10 | Quick summary |
| **Total** | **10:00** | **+1:20** | **11:20 max with buffer** |

**Note**: Buffer time allows for:
- Questions during demo
- Technical hiccups
- Slower internet
- Audience engagement

---

## Talking Points & Key Messages

### Core Message
> "OHM makes multi-facility coordination for complex hardware designs practical and efficient, enabling small-batch, local, urgent production."

### Problem Statement
> "Complex hardware designs require multiple specialized facilities, but manually finding and coordinating them is time-consuming and doesn't scale."

### Solution Statement
> "OHM uses intelligent matching to automatically find the right combination of facilities, organizes results by component for easy decision-making, and generates RFQs to streamline procurement."

### Value Proposition
> "What takes hours or days manually, OHM does in under a minute, making local production and small-batch manufacturing practical."

---

## Transition Phrases

### Between Sections

**Setup → Problem**:
> "But here's the challenge..."

**Problem → Solution**:
> "So the question is: How do you solve this? Let me show you how OHM works..."

**Solution → Impact**:
> "Now, what does this mean in practice? Let me talk about the impact..."

**Impact → Wrap-Up**:
> "To summarize what we've seen..."

### Within Sections

**After showing map**:
> "Now let's look at a specific design..."

**After matching**:
> "Let's dive into what OHM found..."

**After Production Plan**:
> "You can see the detail for each facility..."

**After RFQ**:
> "This automates what would normally be manual work..."

---

## Technical Explanations (If Asked)

### How Matching Works
> "OHM uses a four-layer matching system: direct matching for exact capability matches, heuristic rules for related processes, NLP for semantic understanding, and LLM for complex reasoning. This ensures we find the best matches even when terminology differs."

### Component-Centric Organization
> "We organize by component rather than by facility because that's how users think - 'I need X component, where can I get it?' This makes it easier to make decisions based on location, capacity, or other factors."

### RFQ Generation
> "The RFQ generation extracts all relevant information from the design and matching results, formats it according to standard RFQ templates, and creates ready-to-send documents. This saves hours of manual work."

### Location Information
> "Location is critical for local production decisions. OHM extracts location data from facility records and displays it prominently so users can choose facilities based on proximity for urgent or small-batch production."

---

## Backup Explanations

### If Matching Takes Too Long
> "Complex designs with many components can take 30-60 seconds to match. This is because the system is analyzing requirements against all available facilities and finding the optimal combinations. For simpler designs, matching is much faster."

### If No Matches Found
> "If no matches are found, it could mean the design requires capabilities that aren't available in the current facility database. In a production system, you'd add more facilities or adjust the design requirements."

### If API is Slow
> "The demo connects to a cloud API. If it's slow, we have a local backup deployment we can switch to. The matching algorithm itself is fast - the delay is usually network-related."

### If Something Breaks
> "This is a demonstration system. In production, we'd have more robust error handling and fallback mechanisms. But the core matching and coordination logic is solid and tested."

---

## Practice Notes

### What to Practice
1. **Timing**: Run through full demo and time each section
2. **Transitions**: Practice smooth transitions between sections
3. **Mouse movements**: Minimize unnecessary mouse movement
4. **Pacing**: Don't rush, but stay within time limits
5. **Key messages**: Emphasize core value proposition

### Common Issues to Watch For
- Matching takes longer than expected (have talking points ready)
- Map doesn't load (have backup explanation)
- Location shows "N/A" (should be fixed, but have explanation ready)
- RFQ generation fails (rare, but have backup)

### Smooth Execution Tips
- Pre-load the app before demo starts
- Have a specific design in mind (3D Printed Prosthetic Hand)
- Know which components to highlight
- Practice clicking through sections smoothly
- Have backup explanations ready

---

## Demo Flow Diagram

```
[Start]
  ↓
[Map Overview] → [Design Selection] → [Run Matching]
  ↓                                              ↓
[Problem Statement]                    [Results Overview]
  ↓                                              ↓
[The Challenge]                        [Production Plan]
  ↓                                              ↓
[Transition]                           [Facility Details]
  ↓                                              ↓
[Solution Intro]                       [RFQ Generation]
  ↓                                              ↓
[Matching Execution]                   [Impact & Value]
  ↓                                              ↓
[Results]                              [Wrap-Up]
  ↓                                              ↓
[End] ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

---

## Success Metrics

### Demo is Successful If:
- ✅ Audience understands the problem (multi-facility coordination)
- ✅ Audience sees the solution (automatic matching + organization)
- ✅ Audience understands the value (time savings, local production)
- ✅ Demo completes within 10 minutes
- ✅ All features work as expected
- ✅ Questions can be answered confidently

---

## Post-Demo Q&A Preparation

### Expected Questions

**Q: How accurate is the matching?**
> "The matching uses multiple layers - direct matching for exact matches, heuristic rules for related processes, and NLP for semantic understanding. Confidence scores indicate match quality. For the demo, we're showing matches with high confidence scores."

**Q: Can this work with real facilities?**
> "Yes, this is designed to work with real OKW facility data. The demo uses synthetic data, but the system can ingest real facility capabilities and match them against real OKH designs."

**Q: What about cost estimation?**
> "Cost estimation is a planned feature. The current system focuses on capability matching and coordination. Cost data can be added to facility records and used for cost estimation in future versions."

**Q: How does this handle lead times?**
> "Lead time information can be included in facility data and used for scheduling. The current demo focuses on capability matching, but the system architecture supports lead time integration."

**Q: Can facilities see what's being requested?**
> "The RFQ generation creates documents that can be sent to facilities. In a full system, facilities could have portals to view and respond to RFQs, but that's beyond the current demo scope."

---

## Notes for Refinement

- [ ] Practice timing for each section
- [ ] Refine talking points based on practice
- [ ] Add more specific examples if needed
- [ ] Adjust transitions based on flow
- [ ] Record practice run for review
- [ ] Get feedback on clarity and pacing

---

**Last Updated**: January 12, 2025  
**Next Review**: After practice run
