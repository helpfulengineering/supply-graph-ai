---
copyright:
  link: "https://creativecommons.org/licenses/by/4.0/"
  text: Creative Commons Attribution 4.0 International License
  type: CC-BY
csl: /app/dist/server/server/utils/citations/citeStyles/apa-6th-edition.csl
date:
  day: 26
  month: 01
  year: 2022
journal:
  publisher-name: Internet of Production Alliance
  title: Internet of Production Alliance
link-citations: true
title: Open Know-Where Specification
---

## 1. Introduction

This standard was initiated by the [Internet of Production
Alliance](https://internet-of-production.webflow.io/ "null") and
developed by an open-membership working group. It is designed to create
a consistent way of documenting and sharing information about
manufacturing capabilities to make it easier for people to identify
where hardware can be made locally or anywhere in the world.

This specification is designed to be adopted by anyone who collects or
shares data about manufacturing capabilities, including governments,
non-government organisations (NGOs), aid agencies, mapping communities,
makers and platforms. The standard defines data that meets the needs of
a broad range of use cases and purposes.

We call this "Open Know-Where".

Adopting the Open Know-Where standard will:

-   Improve the discovery of manufacturing facilities and equipment
    within the manufacturing industry and maker communities.

-   Enable someone who wants to access a manufacturing facility to
    discover who they should be contacting.

-   Improve relationships and collaboration between users and networks.

-   Make data about the location of manufacturing capabilities more
    easily discoverable and accessible when needed.

-   Enable better curation and management of data, so it can be
    collated, organised, queried and filtered.

-   Enable the curation of tools to extract the maximum value from the
    data.

Overall, the more universal the standard is, the more useful it will be.
The principle is that it is an open standard, whether or not the data it
is used to describe is released openly. 

The standard covers five concepts (classes) that mapping initatives
typically describe. For each concept, we have aimed to standardise the
properties to an appropriate level of granularity, which is helping
someone to find out where something can be made.

The five classes are:

-   Manufacturing Facility

-   Agent (Persons and Organisation)

-   Location

-   Equipment

-   Materials

Several aspects of the classes can be standardised through
classification and dictionaries. Using this approach means initiatives
and manufacturing facilities can more easily share, compare and
aggregate data. This is important, as currently there is no way to do
this without duplication of field names and data. The ability to easily
share data encourages the building of relationships and collaboration
between users and networks. This will lead to improved documentation,
networking, and discovery of mapping initiatives, manufacturing
facilities and equipment within the manufacturing sectors and maker
communities.

The intention is for data published under Open Know-Where, to be helpful
and informative, rather than authorative. We assume that any procurement
resulting from data published under this standard will still involve
direct or mediated interaction between the user/buyer and the facility.
Future versions of the specification will move towards more rigorous
approaches to defining information to enable distributed procurement
systems.

The project follows on from the success of the [Open
Know-How](https://openknowhow.org/ "null") documentation standard,
released in September 2019.

### 1.1. Scope

This specification defines a standard that provides a mechanism for the
discovery and exchange of the location of manufacturing capabilities and
where to get something made. This reflects the goal established by the
Internet of Production Alliance whose aim is to develop the enabling
technologies and infrastructures to support a global move to distributed
and local manufacturing.  

More information about the Internet of Production Alliance can be found
here: <https://global.us17.list-manage.com/subscribe?u=9ef0e368cc373faed18dbfc77&id=1e6d61b540>

The Open Know-Where specification defines a data model to:

-   Document the location of manufacturing capabilities globally.

-   Share information about manufacturing facilities and the
    manufacturing capabilities.

-   Improve networking within the manufacturing industry and maker
    communities.

The Open Know-Where specification provides the level of detail needed
for quick and simple documentation of manufacturing capbilites and
manufacuting facilities.

Although designed to be used by all, the intended audience is:

-   Mappers

-   Maker communities

-   Governments

-   Non-Government Organisations

-   Aid Agencies

-   Platforms listing local manufacturing capabilities 

The standard does not specify a data format or exchange protocols,
instead it aims to support the wide range of use cases from
spreadsheet-based datasets through to web-based platforms. 

### 1.2. Structure of this Document

This specification is divided into eight main sections:

1.  **Introduction** -- provides a broad overview of the background,
    scope and aim of this standard.

2.  **Data Model Diagram** -- provides an overall view of the Open
    Know-Where Data Model

3.  **Using the Data Model** -- provides guidance about how to use the
    data model, with answers to our most frequently asked questions.

4.  **Manufacturing Facility **-- defines properties relating to the
    manufacturing facility. Recommended classifications and formats are
    also provided for consistency.

5.  **Agent** -- defines properties relating to people and
    organisations. Recommended classifications and formats are also
    provided for consistency.

6.  **Location** -- defines properties relating to locations.
    Recommended classifications and formats are also provided for
    consistency.

7.  **Equipment** -- defines properties relating to equipment.
    Recommended classifications and formats are also provided for
    consistency.

8.  **Materials** -- defines properties relating to materials.
    Recommended classifications and formats are also provided for
    consistency.

9.  **Record Data **-- defines properties relating to record data.
    Recommended formats are also provided for consistency.

### 1.3. Technical Authoring

Technical authoring for version 1.0 has been undertaken by [Barbal
Limited](https://barbal.co/technical-and-professional-services/ "null").

The standard has been developed under the guidance of the Open
Know-Where working group following a series of qualitative interviews
with members of NGOs, aid agencies, mapping communities, makers and
platforms, and analysis into datasets shared by mapping initiatives and
organisations. From this initial research, a conceptual data model was
developed and circulated to stakeholders for comment. This document is
the formalisation of that data model and includes descriptions of each
aspect and guidance for how mapping initiatives can adopt the
standardised approach it prescribes.

### 1.4. Working Group Members

The following have contributed directly towards the development of this
specification.

  **Name**                   **Organisation**
  -------------------------- --------------------------------------------------------
  Andrés Barreiro            Wikifactory
  Charles Barrete            Field Ready
  Pierre-Alexis Ciavaldini   Makernet
  Liz Corbin                 Metabolic
  Guillaume Coulombe         Fab Labs Québec / Procédurable
  Marc-Olivier Duchame       Fab Labs Nation
  Andrew Lamb                Field Ready / Internet of Production Alliance
  Anna Sera Lowe             Manufacturing Change / Internet of Production Alliance
  Bryn John                  Field Ready
  Ben Oldfrey                UCL
  Nathan Parker              MakerNet.work
  James Ochuka               Juakali Smart
  Alessandra Schmidt         Make Works
  Hannah Stewart             RCA / Dark Matter Labs
  Aziz Wadi                  Field Ready
  Anna Waldman-Brown         MIT

More people than those listed here have been consulted, and we still
welcome any additional input from anyone who wants to get involved with
Open Know-Where.

## 2. Data Model Diagram

This diagram illustrates the classes, properties and relationships that
are introduced in the following main sections.

Whilst the model represents a relational schema between concepts, it is
not anticipated that all initiatives would use the whole model. The
schema is designed so that individual initiatives can focus only on
certain aspects and then data can be aggregated between data sets to
create richer, more powerful insight. 

For example an initiative to create an open database of equipment
capabilities by make and model could be combined with a mapping
initiative of maker spaces in a region which lists the make and model of
the equipment available to help someone work out where the specific
manufacturing processes they need can be accessed. 

![Open Know-Where data model diagram showing the relationships between
aspects of the standard\'s data
fields](https://assets.pubpub.org/556zgshv/71640173669266.png){#nql597kgrpu}

Open Know-Where data model

## 3. Using Open Know-Where

### 3.1. Can anyone use Open Know-Where?

Anyone can adopt the data model. It has been designed to be applied
across a variety of use cases, and provides a level of detail needed for
quick and simple mapping and recording of manufacturing capabilities and
manufacturing facilities. It can be used by formal and informal
organisations, and anyone who is mapping manufacturing capbabilities and
manufacturing facilities.

### 3.2. My resources are only available to members, will I have to give access for free?

No, this standard does not change your access models to your content.

### 3.3. Is this all about publishing data online?

Not necessarily. The primary purpose of Open Know-Where is to make it
easier to share information between mapping initiatives and other
entities who can make use of the data. We do not anticipate that many
data initiatives will choose to publish all the information openly
online and advise mapping initiatives to consider the privacy and
security of facilities, organisations and individuals and the
permissions (implied or explicit) they have for using the information
they have collected or recieved.  In some cases it will be prudent to
redact information to make is suitable for publishing online, e.g. state
the city and not a full address, or provide a login wall to access
contact information.

### 3.4. How is Classification Achieved?

[Naming
conventions](https://en.wikipedia.org/wiki/Naming_convention#:~:text=A%20naming%20convention%20is%20a,the%20names%20based%20on%20regularities. "null") allow
useful information to be deduced from regularity, will prevent confusion
among others who are collecting the same or similar data, and make it
easier for others to interpret your data.

By using a naming convention such as Wikipedia, the classification
simply provides a relevant Wikipedia URL and references the
corresponding Wikipedia article to the concept being described. For
example, through this way of classification, you can use the
corresponding Wikipedia article for a manufacturing process, to define
the process capability of a facility. The same can be applied for
equipment and materials. This manner of classification makes
manufacturing processes, equipment and materials easy to navigate and
provides consistency across the classification.

For example, for the metal-joining process of Brazing:

Wikipedia article: <https://en.wikipedia.org/wiki/Brazing>

### 3.5. How do I use the classification system?

To aid consistency, Open Know-Where recommends using an existing
classification system for Equipment, Manufacturing Processes and
Materials. This being Wikipedia.

**To classify equipment:**

To reference a facility has a piece of equipment, for example a
soldering iron, you would simply copy and paste the Wikipedia URL for a
soldering iron into the relevant field.

Wikipedia article: <https://en.wikipedia.org/wiki/Soldering_iron>

**To classify a manufacturing process:**

To classify a manufacturing process, for example soldering, you would
simply copy and paste the relevant Wikipedia URL for soldering into the
relevant field.

Wikipedia article: <https://en.wikipedia.org/wiki/Soldering>

**To classify a material:**

To reference a material, for example aluminium, you would simply copy
and paste the relevant Wikipedia URL for aluminium into the relevant
field.

Wikipedia article: <https://en.wikipedia.org/wiki/Aluminium> 

### 3.6. What data format is the data model designed to support?

The scheme is designed to support any structured data format. There is
no recommendation for how the data is stored or transferred.

### 3.7. Which standards does the specification use?

Rather than creating classifications for Equipment, Manufacturing
Processes and Materials we have used Wikipedia as reference.

The specification also references [ISO
8601](https://www.iso.org/iso-8601-date-and-time-format.html "null"),
the format YYYY-MM-DD for date, and [ISO
639-2](https://www.iso.org/iso-639-language-codes.html "null") or [ISO
639-3](https://iso639-3.sil.org/code_tables/639/data "null"), for
example "en-gb", to
record [Languages](https://standards.internetofproduction.org/pub/okw#languages "null").

### 3.8. Is Open Know-Where compatible with Open Know-How?

Open Know-Where is more detailed than Open Know-How version 1, which
only extends as far a signposting the documentation for making things.
We anticipate that later versions of Open Know-How will apply the same
approach as Open Know-Where for classifying equipment, materials and
processes so that the two standards will be fully interoperable.

### 3.9. What do the properties and sub-properties mean?

This section defines the layout used for defining properties. The list
of properties are laid out in sections four, five, six, seven and eight.
Each of these sections are navigated by the label assigned to each
individual field.

Sub-properties are used to group properties that relate to a specific
concept and that might be applicable in specific circumstance (e.g.
educational aspects of an innovation space).

For each property, the following specification is given where
applicable.

  **Label**        The human readable name assigned to the term.
  ---------------- ----------------------------------------------------------------------------------------------------
  **Fieldname**    The standardised computer readable fieldname. Typically this is the label expressed in camel case.
  **Definition**   A statement which represents the concept of the term.
  **Format**       The recommended practice for the field.
  **Note**         Additional points of note.
  **Example**      An illustration of how the term can be used.

### 3.10. Is the entire specification mandatory?

No aspect of the specification is mandatory. However the more
rigourously the specification is followed, the more useful the data will
be to others when shared.

The Open Know-Where working group intends to develop implementation
guides for specific use cases which may make certain aspects mandatory
in certain situations, e.g. Humanitarian applications may specify that
certain formats are used for fields or the Humanitarian Exchange
Language (HXL) is used for location.

### 3.11. Some of my data is sensitive and I don't want to share it. {#some-of-my-data-is-sensitive-and-i-dont-want-to-share-it}

That's fine. You should make a decision as to whether the information
you share will comprimise the trust, privacy or security of the
facilities or individuals the information relates to and apply a risk
based approach when deciding how you share data and who with.

### 3.12. Can I use Open Know-Where with spreadsheets?

Absolutely, the standard is designed to work with any structured data
format. The design is such that we expect that you will use separate
sheets within a workbook for each of the five classes and then use a
primary key or other spreadsheet functionality to link between them.

### 3.13. Which data serialisation format should I use?

Open Know-Where is compatible with any data serialisation format, for
example, XML, JSON, and YAML. It may be helpful to speak with who you
are exchanging data with to find out which format is most appropriate.

### 3.14. How does Open Know-Where deal with linked data across datasets?

We have not made any recommendation for how to link related data between
datasets, however each class has fields (or combination of fields) which
can be used as unique references. 

### 3.15. Will it be a lot of work to revise my existing datasets to be compatible with Open Know-Where?

Possibly. The data model doesn't require you to capture new data, as it
is not mandatory to use all the properties, but you may have to
restructure your data. The amount of work will be dependent on the size
of your datasets.

### 3.16. What if I want to capture information that isn't covered by Open Know-Where?

You are free to extend the fields you use in your own datasets, they
just might not be recognised by others. If you think your properties
would be a useful addition to the Open Know-Where specification itself
for others to use, contact the working group and recommend the
additions.  

## 4. Manufacturing Facility Properties

This class incorporates the important properties relating to
'Manufacturing Facility'. By facility we mean the workspace used for
manufacturing.

There are many different types of workspaces, ranging from industrial
facilities such as factories, to small scale production facilities such
as workshops, to makerspaces, even individual craftspeople working from
home. The aim of Open Know-Where is to incorporate and capture the
properties that are common to all of them, and also to define important
fields that are only applicable to certain types of manufacturing
facilities. For example, for innovation type spaces we have included
sub-properties such as Learning Resources, which is not relevant to all
manufacturing facilities but important to those within maker
communities.

Where properties are logically grouped, such as 'Human Capacity' and
'Innovation Space Properties', they are presented as collections of
sub-properties.

![Manufacturing facility data model diagram showing the relationship
between the standard\'s data fields related to manufacturing
facilities](https://assets.pubpub.org/c7wmzvbh/61640174340634.png){#ncg3eot8o7c}

### 4.1. Name

**Definition: **Name of the facility.

**Format: **Provide the name of the facility.

### 4.2. Location

**Definition: **Location of the facility.

**Format: **Uses
the [Location](https://standards.internetofproduction.org/pub/okw#location-properties "null") class.

### 4.3. Owner

**Definition: **An [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") who
owns or manages the facility.

**Format: **Uses
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

### 4.4. Contact

**Definition: **An [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") who
is the contact for enquiries about making.

**Format: **Uses
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

### 4.5. Affiliation

**Definition: **The [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null")(s)
who the manufacturing facility is affiliated with.

**Format: **Uses
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

**Note: **An affiliation can be used to define the facility type, for
example an affiliation with FabLabs.org implies that the facility is a
FabLab.

### 4.6. Facility Status

**Definition: **Status of the facility.

**Format: **Use of one the following:

-   Active

-   Planned

-   Temporary Closure

-   Closed

### 4.7. Opening Hours

**Definition: **Hours in which the facility operates.

**Format: **Free text.

### 4.8. Description

**Definition:** Description of the facility.

**Format: **Free text.

### 4.9. Date Founded

**Definition: **Date the facility was founded.

**Format: **Recommended practice is to use [ISO
8601](https://www.iso.org/iso-8601-date-and-time-format.html "null"),
i.e. the format YYYY-MM-DD.

**Note: **It is acceptable to include only the Year (YYYY) or year and
month (YYYY-MM).

### 4.10. Access Type

**Definition: **How the manufacturing equipment is accessed.

**Format: **Use one of the following:

-   Restricted (only certain people (e.g. staff members) can use the
    equipment)

-   Restricted with public hours (the equipment can be used by the
    public during limited hours)

-   Shared space (the facility is a shared workspace where access is by
    qualifying criteria (e.g. rental of a desk or workspace))

-   Public (anyone may use the equipment (e.g. training may be required
    and other restrictions may apply))

-   Membership (access requires membership, which is available to the
    public or a certain demographic)

**Note:** For facilities, use this field on a general-terms basis (i.e.
if most equipment is available to members, but certain equipment
requires staff to operate use Membership). This field can also be used
as a property of individual equipment where a facility has different
aspect types for different equipment.

### 4.11. Wheelchair Accessibility

**Definition: **Whether the manufacturing facility is wheelchair
accessible.

**Format: **Free text.

### 4.12. Equipment

**Definition: **The equipment available for use at the manufacturing
facility.

**Format: List the equipment available using
the **[Equipment](https://barbal.co/the-open-know-where-specification/#4ff07f8c-32cd-415c-bceb-1704defc1c26 "null") class.

### 4.13. Manufacturing Processes

**Definition: **Typical manufacturing processes undertaken at the
facility.

**Format: Reference the relevant Wikipedia article.**

**Note: **For instructions how to do this, please see [section
3.5](https://barbal.co/the-open-know-where-specification/#a415a370-91a1-4ec2-a9fb-a0fc05a9be1e "null").

### 4.14. Typical Batch Size

**Definition: **Typical batch size output.

**Format: ** Use one of the following:

-   0 -- 50 units

-   50 -- 500 units

-   500 -- 5000 units

-   5000 + units

### 4.15. Size / Floor Size

**Definition: **The size or floor size of a manufacturing facility.

**Format: **Integer. Unit: square metres (sqm).

**Note: **This helps a prospective user gauge the scale of a
manufacturing facility.

### 4.16. Storage Capacity

**Definition: **Storage Capacity of the manufacturing facility.

**Format:** Free text.

**Note: This helps a prospective user gauge how much storage capacity a
manufacturing facility has for producing and storing stock.**

### 4.17. Typical Materials

**Definition: **Typical materials used by the facility.

**Format: Uses
the **[Materials](https://standards.internetofproduction.org/pub/okw#materials-properties "null")** class.**

### 4.18. Certifications

**Definition: **Certifications obtained by the facility.

**Format: **List the certifications.

**Note: **Knowledge of these is imperative informal manufacturing and
procurement. For example, aid agencies would be able to see which
manufacturing facilities have particular manufacturing licenses, such as
medical manufacturing.

### 4.19. Backup Generator

**Definition:** Whether a manufacturing facility has a backup generator.

**Format: **TRUE / FALSE

**Note: Knowledge of this is particiularly useful in places where there
are frequent power outages.**

### 4.20. Uninterrupted Power Supply

**Definition: **Whether a manufacturing facility has an uninterrupted
power supply.

**Format: **TRUE / FALSE

### 4.21. Road Access

**Definition: **Whether a manufacturing facility has road access.

**Format: **TRUE / FALSE

### 4.22. Loading Dock

**Definition: **Whether a manufacturing facility has a loading dock.

**Format: TRUE / FALSE**

### 4.23. Maintenance Schedule

**Definition: **The maintenance schedule of a manufacturing facility.

**Format: **Free text.

### 4.24. Typical Products

**Definition:** Typical products produced by the facility.

**Format: **List the typical products produced.

### 4.25. Partner / Funder

**Definition: **The [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") which
partners or funds the facility.

**Format: Uses
the **[Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

### 4.26. Customer Reviews

**Definition: **Customer reviews of the facility.

**Format: **Free text.

### 4.27. Circular Economy sub-properties

This section relates to Circular Economy. The definition of Circular
Economy used can be
found [here](https://en.wikipedia.org/wiki/Circular_economy "null").

#### 4.27.1. Circular Economy

**Definition: **Whether a manufacturing facility applies Circular
Economy principles.

**Format: **TRUE / FALSE

#### 4.27.2. Description {#description}

**Definition: **Definition of how Circular Economy principles are
applied.

**Format:** Free text.

#### 4.27.3. By-products

**Definition: **List of the by-products produced.

**Format: **Uses
the [Materials](https://standards.internetofproduction.org/pub/okw#materials-properties "null") class.

### 4.28. Human Capacity sub-properties

**Definition: **The human capacity of the facility sub-properties.

#### 4.28.1. Headcount

**Definition: **The headcount of the facility in FTE, using definition
provided [here](https://en.wikipedia.org/wiki/Full-time_equivalent "null").

**Format: **Integer.

**Note: **It is useful for a user / NGO / aid agency to determine the
scale of the facility.

#### 4.28.2. Maker

**Note:** Identified as future work.

### 4.29. Innovation Space sub-properties

**Definition: **The innovation space sub-properties.

#### 4.29.1. Staff

**Definition:** Number of staff supporting the innovation and
educational aspects of the facility.

**Format: **Integer.

**Note: **It is useful to help determine the scale of the facility.

#### 4.29.2. Learning Resources

**Definition: **The learning resources available at the facility.

**Format: **List the learning resources.

**Note: **It is useful for a user to be aware of any learning resources
-- courses, educational classes etc., a manufacturing facility may have
/ run.

#### 4.29.3. Services

**Definition: **The services provided by a manufacturing facility.

**Format: **List the services provided.

#### 4.29.4. Footfall

**Definition: **The footfall at a manufacturing facility.

**Format: **Integer.

**Note: **It is useful to help determine the scale of the manufacturing
facility.

#### 4.29.5. Residencies

**Definition: **Where residencies are available at a manufacturing
facility.

**Format:** TRUE / FALSE

## 5. Agent Properties

This class incorporates properties relating to 'Agent'. Mapping
initiatives capture different relationships, ranging from owners,
managers, funders, contact, people, members, and so on. In order to
categorise this, we have standardised the properties of people and
organisations, or 'agent' as an umbrella term. We have decided to keep
people and organisations combined in a single class because they are
often interchangeable. For example, an owner could be a person or an
organisation.

Some properties such as 'Contact' and 'Social Media', have been
developed further to include important sub-properties. For example, the
inclusion of 'Social Media' sub-properties was incorporated as many
mapped Fab Labs did not have their own URL website, but used Facebook to
promote their facility, projects and capabilities.

Where properties are logically grouped, they are presented as
collections of sub-properties.

![](https://assets.pubpub.org/6hvlk6nd/21640175866625.png){#n1a61sxlriw}

Agent data model

### 5.1. Name {#name}

**Definition: **The name of
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null").

**Note: **This could be a name of a person or an organisation.

### 5.2. Location {#location}

**Definition: **A [Location](https://standards.internetofproduction.org/pub/okw#location-properties "null").

**Format: **Uses
the [Location](https://standards.internetofproduction.org/pub/okw#location-properties "null") class.

### 5.3. Contact Person

**Definition: **An [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") who
is the key point of contact for a manufacturing facility or
organisation.

**Format:** Provide the name of
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null").

### 5.4. Bio

**Description: **A description of a person or an organisation.

**Format: **Free text.

### 5.5. Website

**Definition: **Website address.

**Format: **Provide the relevant URL.

### 5.6. Languages

**Definition: **Languages used by a person or an organisation.

**Format: **[ISO
639-2](https://www.iso.org/iso-639-language-codes.html "null") or [ISO
639-3](https://iso639-3.sil.org/code_tables/639/data "null"), for
example "en-gb".

**Note: **Often manufacturing facilities may be able to provide services
dealing in more than one language.

### 5.7. Mailing List

**Definition: **Mailing list for an organisation.

### 5.8. Images / Media

**Definition: **Images / Media of a person, an organisation, or relating
to the manufacturing facility.

### 5.9. Contact sub-properties

**Description: **Defined contact information.

#### 5.9.1. Landline

**Definition: **A landline telephone number to contact the facility,
person or organisation.

**Format: **Provide the telephone number.

#### 5.9.2. Mobile

**Definition: A mobile telephone number to contact the facility, person
or organisation.**

**Format: **Provide the telephone number.

#### 5.9.3. Fax

**Definition: A fax number to contact the facility, person or
organisation.**

**Format: **Provide the fax number.

#### 5.9.4. Email

**Definition: **An email address to contact the facility, person or
organisation.

**Format: **Provide the email address.

#### 5.9.5. WhatsApp

**Definition: **A WhatsApp number to contact the facility, person or
organisation.

**Format: **Provide the telephone number.

**Note: **In some instances, users contact the manufacturers through
WhatsApp.

### 5.10. Social Media sub-properties

**Description: **Defined social media information.

#### 5.10.1. Facebook

**Definition: **Facebook page URL.

**Format: **Provide the relevant URL.

**Note: **Facebook is an important platform for contacting Fablabs /
other manufacturing facilities. For example, in the Philippines, a
Facebook group has been created for all Fablabs to interact through.

#### 5.10.2. Twitter

**Definition: **Twitter page URL.

**Format: **Provide the relevant URL.

**Note: Manufacturing facilities often promote themselves, their
activities and projects on Twitter.**

#### 5.10.3 Instagram

**Definition: **Instagram page handle.

**Format:** Provide the relevant Instagram handle.

**Note: Manufacturing facilities often promote themselves, their
activities and projects on Instagram.**

#### 5.10.4 Other URLs

**Definition: **Other URLs.

**Format: **Provide the relevant URLs.

**Note: Other examples of social media associated with a manufacturing
facility, organisation or person, unclassified by this standard, but can
also be included. For
example, **[**fablabs.io**](https://fablabs.io/labs "null")** or **[**hackerspaces.org**](https://hackerspaces.org/ "null")**.**

## 6. Location Properties

This class incorporates the important properties relating to 'Location'.

A simple standardised way of capturing geographical information is
imperative -- to be able to use a 'Manufacturing facility' or
'Equipment', a user needs to know its location. The properties below
describe the core characteristics which are needed for data collection.

Recording a geographical location differs globally. In the developed
world, an 'Address' such as a street address, is the norm for recording
places of interest. Whereas, in some countries, a description of the
location -- i.e. 'near the school, on this corner', is an adequate
description of location. When recording data, the latter qualitative
data is subjective, and difficult to quantify. As such, an addressing
system which is not a street address is incredibly useful. Consequently,
the application of '[GPS
coordinates](https://standards.internetofproduction.org/pub/okw#gps-coordinates "null")'
and '[What 3
Words](https://standards.internetofproduction.org/pub/okw#what-3-words-sub-properties "null")'
have been integrated into the Open Know-Where data model. Both 'GPS
coordinates' and 'What 3 Words' are already in use by many NGOs and Aid
Agencies when recording the 'Location' of manufacturing facilities
and/or 'Equipment'.

For compatibility with the [Humanitarian Exchange
Language](https://hxlstandard.org/standard/1-1final/ "null"), use
the [HXL hashtag
chooser](https://hxlstandard.github.io/hxl-hashtag-chooser/ "null").

Where properties are logically grouped, they are presented as
collections of sub-properties.

![](https://assets.pubpub.org/6oo7rpuq/21640188254529.png){#nriusmhjam5}

Location properties data model

### 6.1. Address

**Definition: **Address relating to a manufacturing facility, person or
organisation.

**Format: **Use the defined Address sub-properties:

-   Number

-   Street

-   District

-   City

-   Region

-   Country

-   Postcode

**Note: **Address has been standardised to include these fields for ease
of use, discoverability and merging data sets.

For compatibility with the [Humanitarian Exchange
Language](https://hxlstandard.org/standard/1-1final/ "null"), use
the [HXL hashtag
chooser](https://hxlstandard.github.io/hxl-hashtag-chooser/ "null").

### 6.3. GPS Coordinates

**Definition: **The relevant GPS coordinates.

**Format: **Provide the relevant GPS coordinates, using [Decimal
Degrees](https://en.wikipedia.org/wiki/Decimal_degrees#:~:text=Decimal%20degrees%20(DD)%20express%20latitude,as%20OpenStreetMap%2C%20and%20GPS%20devices. "null").

**Note: ** GPS coordinates are a common standardised way of detailing a
location, used by many aid agencies and mapping initiatives.

### 6.4. Directions

**Definition: **Directions to manufacturing facility, person or
organisation.

**Format: **Free text.

**Note: **This qualitative data field may be helpful for a difficult to
find location, or in an area where the standard address format is
irrelevant.

### 6.5. What 3 Words sub-properties

**Definition: **The What 3 words address for the location.

#### 6.4.1. What 3 Words

**Definition: **What 3 Words phrase for location.

**Format: **State the What 3 Words phrase.

**Note:** Often informal settlements, or developing countries do not
have street addresses, and communicating GPS coordinates can be tricky
and error-prone. What 3 Words is an alternative geospatial address
system.

Every location has been a 3m x 3m grid square with a 3 word address.
Meaning you can collect, validate and provide any location within a 3m x
3m radius with just 3 words. For example: Barbal's office in Bristol is
recorded as '///shares.parks.alone'.

#### 6.4.2. Language

**Definition: **Language What 3 Words has been recorded in.

**Format: **[ISO
639-2](https://www.iso.org/iso-639-language-codes.html "null") or [ISO
639-3](https://iso639-3.sil.org/code_tables/639/data "null"), for
example "en-gb".

**Note: **What 3 Words is available in 43 different languages and the
words for an address are not direct translations of each other.

## 7. Equipment Properties

This class incorporates the properties relating to Equipment. It
provides a simple standardised way of capturing the manufacturing
capabilities of equipment.

A key aspect which arose, is the scope, and specifically -- what are we
trying to capture? For example, only machines and digital equipment? Or
can we capture hand tools, IT equipment, software, and so on?

Knowing that a CNC router may be important may be useful in decision
making for deciding where to get something made, but generic hand tools
may not, but that does not preclude them from being included when
documenting. This resulted in needing a simple classification system
which would standardise a wide variety of Equipment.

The potential list of properties for Equipment is boundless but, Open
Know-Where aims to standardise as many as possible. We expect this list
to grow with time with different recommended properties for different
classes of equipment/tools.

Where properties are logically grouped, they are presented as
collections of sub-properties. 

![](https://assets.pubpub.org/0u0vpclg/71640188545208.png){#npvtnepjs4z}

### 7.1. Equipment Type

**Definition: **Classification of Equipment.

**Format: **Provide the Wikipedia URL for the relevant Equipment Type.

**Note: **For instructions how to do this, please see [section
3.5](https://standards.internetofproduction.org/pub/okw#how-do-i-use-the-classification-system "null").

### 7.2. Manufacturing Process

**Definition: **Manufacturing process the Equipment is capable of.

**Format: **Provide the Wikipedia URL for the relevant manufacturing
process.

**Note: **For instructions how to do this, please see [section
3.5](https://standards.internetofproduction.org/pub/okw#how-do-i-use-the-classification-system "null").

### 7.3. Make

**Definition: **Make of the piece of equipment.

**Format: **Provide the make of the model.

**Note:** Provides detailed information about a piece of equipment/tool.
For example, you can design generically for a 3D printer, or you can
design for a specific make or model of 3D printer.

### 7.4. Model

**Definition: **Model of the piece of Equipment.

**Format: **Provide the name of the model.

**Note: **Provides detailed information about a piece of equipment. For
example, you can design generically for a 3D printer, or you can design
for a specific make or model of 3D printer.

### 7.5. Serial Number

**Definition: **Serial number of the piece of Equipment.

**Format: **Provide the serial number of the Equipment.

### 7.6. Location {#location}

**Definition: **Location of the equipment.

**Format: **Uses [Location](https://barbal.co/the-open-know-where-specification/#e234eb65-ff36-4343-8c4a-cb9d7c02342f "null") class.

### 7.7. (Skills Required)

***Identified as future work.***

### 7.8. Condition

**Definition: **The condition of the piece of equipment.

**Format: **State the condition of the piece of equipment.

**Note:** This provides a user with information surrounding the quality
of a piece of equipment/tool, and whether it can complete the task they
need it for.

### 7.9. Notes

**Definition: **Additional information about the piece of equipment.

**Format: **Free text.

### 7.10. Owner {#owner}

**Definition:** The owner of a piece of equipment.

**Format: **Uses
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

**Note:** To be used when the owner is not the manufacturing facility.

### 7.11. Quantity

**Definition: **Quantity of specific piece of equipment.

**Format:** Integer.

**Note:** This provides information surrounding the size and scale of a
manufacturing facility and implicates batch size.

### 7.12. Throughput

**Definition: **The throughput of the piece of equipment.

**Format: **Free text.

### 7.13. Power Rating

**Definition: **The power rating of the piece of equipment.

**Format: **Integer. Unit: W.

### 7.14. Materials Worked

**Definition: **The materials that can be used with the piece of
equipment.

**Format: **Uses
the [Materials](https://standards.internetofproduction.org/pub/okw#materials-properties "null") Classification. 

### 7.15. Maintenance Schedule {#maintenance-schedule}

**Definition: **When the equipment was last maintained.

**Format: **Free text.

### 7.16. Usage Levels

**Definition: **How often the piece of equipment is used.

**Format: **Free text.

### 7.17. Tolerance Class

**Definition: **The tolerance class of the piece of equipment.

**Format: **In accordance with [ISO
2768](https://www.plianced.com/compliance-wiki/iso-2768-general-geometrical-tolerances-and-technical-drawings/ "null").

### 7.18. Current Firmware

**Definition: **The current firmware used by the piece of equipment.

**Format: **Free text.

### 7.19. Uninterrupted Power Supply {#uninterrupted-power-supply}

**Defintion: **Whether the piece of equipment has an uninterrupted power
supply.

**Format: **TRUE / FALSE

### 7.20. Defined sub-properties 

These are specialised properties that only apply to specific types of
equipment. In this section th**e list of Equipment Properties provided
is extensible, and hasn't attempted to be exhaustive. The Equipment
sub-properties provided represent a significant proportion of equipment
used in manufacturing facilities. The below list of defined
sub-properties has been provided in alphabetical order for ease of use
and reference.**

#### 7.20.1. Axes

**Definition: **The number of axes.

**Format: **Integer.

#### 7.20.2. Bed Size

**Definition: **The bed size of a piece of equipment.

**Format: **Integer. Unit: mm.

#### 7.20.3. Bending Length

**Definition: **Length of bending.

**Format: **Integer. Unit: mm.

#### 7.20.4.Build Volume {#7204build-volume}

**Definition: **The dimensions of the build.

**Format: **Integer. Unit: mm\^3.

#### 7.20.5. Chuck Jaw Diameter

**Definition: **The diameter of the chuck jaw.

**Format: **Integer. Unit: mm.

#### 7.20.6. Collet Size

**Defintion: **The size of the collet.

**Format: **Integer. Unit: mm.

#### 7.20.7. Computer Controlled

**Definition: **Whether the equipment is computer controlled.

**Format: **TRUE / FALSE

#### 7.20.8. Cross Slide Travel

**Definition: **Distance of Cross Slide Travel.

**Format: **Integer. Unit: mm.

#### 7.20.9. Daylight / Opening

**Definition: **Daylight / Opening size.

**Format: **Integer. Unit: mm.

#### 7.20.10. Distance Between Centres

**Definition:** The distance between a centre in the headstock and a
centre in the tailstock.

**Format: **Integer. Unit: mm.

#### 7.20.11. Ejector Threads

**Definition: **Ejector Thread Size.

**Format:** Integer. Unit: mm.

#### 7.20.12. Extraction System

**Definition: **Is there an extraction system?

**Format: **TRUE / FALSE

#### 7.20.13. Gantry Material

**Definition: **The material the gantry is made out of.

**Format: **Uses [Material](https://standards.internetofproduction.org/pub/okw#materials-properties "null") class.

#### 7.20.14. Hot Runner Compatible

**Definition: **Whether the equipment is hot runner compatible.

**Format: **TRUE / FALSE

#### 7.20.15. Laser Power

**Definition: **Power consumption used.

**Format:** Integer. Unit: W.

#### 7.20.16. Layer Resolution

**Definition: **Thickness of layer.

**Format: **Integer. Unit: mm.

#### 7.20.17. Locating Ring Diameter

**Definition: **Diameter of the locating ring.

**Format: **Integer. Unit: mm.

#### 7.20.18. Material Worked

**Definition: **The type of material worked on the equipment.

**Format: **METAL / NON-METAL

#### 7.20.19. Maximum Clamping Force

**Definition: **The maximum clamping force of the equipment.

**Format:** Integer. Unit: t.

#### 7.20.20. Maximum Shot Volume

**Definition: **The maximum shot volume.

**Format: **Integer. Unit: mm\^3.

#### 7.20.21. Maximum Spindle Speed

**Definition: **The maximum spindle speed.

**Format:** Integer. Unit: rpm.

#### 7.20.22. Maximum Tie Bar Distance

**Definition: **The maximum tie bar distance.

**Format: **Integer. Unit: mm.

#### 7.20.23. Nozzle Size

**Definition: **Size of nozzle.

**Format: **Integer. Unit: mm.

#### 7.20.24. Nozzle Radius

**Definition: **Radius of the nozzle.

**Format:** Integer. Unit: mm.

#### 7.20.25. Optimal Material

**Definition: **The optimal material for use with a piece of equipment.

**Format: **Uses [Material](https://standards.internetofproduction.org/pub/okw#materials-properties "null") class.

#### 7.20.26. Pieceholding Type

**Definition: **How the part is fixed.

**Format: **Free text.

#### 7.20.27. Press Force

**Definition: **The press force.

**Format: **Integer. Unit: kN.

#### 7.20.28. Punch Force

**Definition: **The punch force.

**Format: **Integer. Unit: kN.

#### 7.20.29. Spindle Rotation

**Defintion: **The spindle rotation.

**Format: **Integer. Unit: Deg.

#### 7.20.30. Stations

**Definition: **The number of stations.

**Format: **Integer.

#### 7.20.31. Station size

**Definition: **The size of the station.

**Format: **Integer. Unit: mm.

#### 7.20.32. Tailstock Sleeve Travel

**Definition: **Distance of tailstock sleeve travel.

**Format: **Integer. Unit: mm.

#### 7.20.33. Tooling Type

**Definition:** The tooling type.

**Format: **Free text.

**Example: **Forming, Piercing.

#### 7.20.34. Turning Capacity / Swing

**Definition: **The turning capacity / swing of a piece of equipment.

**Format: **Integer. Unit: mm.

#### 7.20.35. Working Surface

**Definition: **The working surface of a piece of equipment.

**Format:** Integer. Unit: mm.

#### 7.20.36. X Travel

**Definition: **Distance of X travel.

**Format: **Integer. Unit: mm.

#### 7.20.37. Y Travel

**Definition: **Distance of Y travel.

**Format: **Integer. Unit: mm.

#### 7.20.38. Z Travel

**Definition: **Distance of Z travel.

**Format: **Integer. Unit: mm.


## 8. Materials Properties

This class incorporates properties relating to ƒwhat 3s. In general,
materials are outside of the scope for Open Know-Where, however a simple
standardised way of capturing materials is important. For instance, to
be able to use a manufacturing facility, a user needs to be aware of
what materials are available or commonly used at a specific location, or
to use a piece of equipment, a user will need to know what material the
machine is callibrated for. Materials are decisive facet of whether
something can be made at a specific manufacturing facility. 

Consequently, a simple standardised way of capturing materials is
provided by Open Know-Where, but future work to fully standardise
material classifications may be needed, and is currently being
investigated by the Internet of Production Alliance.

Where properties are logically grouped, they are presented as
collections of sub-properties. 

![](https://assets.pubpub.org/tum7vb24/41641401551202.png){#n08yscccr0n}

### 8.1. Manufacturer

**Definition: **The manufacturer of the material type.

**Format:** Free text.

### 8.2. Brand

**Definition: **The brand of the material type.

**Format: **Free text.

### 8.3. Supplier Location

**Definition: **Place of immediate supply to the facility.

**Format: **Use [Location](https://standards.internetofproduction.org/pub/okw#location-properties "null") class.

**Note: **This is not to be used for the location of the manufacturer of
the material, but where the facility gets the material from.

### 8.4. Material Type

**Definition: **Type of material.

**Format: **Provide the Wikiepedia URL for the relevant material type.

**Note: **For instructions how to do this, please see [section
3.5](https://standards.internetofproduction.org/pub/okw#how-do-i-use-the-classification-system "null").

### 8.5. Defined Material Types

In order to support interoperability across datasets, this section sets
out a standardised list of material types used in manufacturing.The list
is not intended to be exhaustive, but extensive enough to capture the
most common types of materials. 

In compiling the list, the level of specificity was deemed important. If
the list is too high-level, it  would not help a buyer or maker
determine if a facility is appropriate for their specific needs. If it
is too detailed a search could exclude equipment that could easily be
applied to similar materials. The figure below provides examples of the
level of specificity for different material types, which was used to
guide decision making in producing this list.

![](https://assets.pubpub.org/952oxiwk/21641401663620.png){#njqten8upzp}

Headings are included in the list to aid navigation by users of the
standard, but do not form part of the classification scheme and should
not be used in Open Know-Where datasets.

#### 8.5.1. Plastics

[HDPE](https://en.wikipedia.org/wiki/High-density_polyethylene "null")

[PLA](https://en.wikipedia.org/wiki/Polylactic_acid "null")

[ABS](https://en.wikipedia.org/wiki/Acrylonitrile_butadiene_styrene "null")

[PET](https://en.wikipedia.org/wiki/Polyethylene_terephthalate "null")

[Acetate](https://en.wikipedia.org/wiki/Cellulose_acetate "null")

[PVC](https://en.wikipedia.org/wiki/Polyvinyl_chloride "null")

[Nylon](https://en.wikipedia.org/wiki/Nylon "null")

[Polycarbonate](https://en.wikipedia.org/wiki/Polycarbonate "null")

[Polypropylene](https://en.wikipedia.org/wiki/Polypropylene "null")

[Acrylic](https://en.wikipedia.org/wiki/Acrylic "null")

#### 8.5.2. Metals

[Iron](https://en.wikipedia.org/wiki/Iron "null")

[Steel](https://en.wikipedia.org/wiki/Steel "null")

[Stainless Steel](https://en.wikipedia.org/wiki/Stainless_steel "null")

[Mild Steel](https://en.wikipedia.org/wiki/Carbon_steel "null")

[Galvanised
Steel](https://en.wikipedia.org/?title=Galvanized_steel&redirect=no "null")

[Aluminium](https://en.wikipedia.org/wiki/Aluminium "null")

[Copper](https://en.wikipedia.org/wiki/Copper "null")

[Zinc](https://en.wikipedia.org/wiki/Zinc "null")

#### 8.5.3. Wood Products

[Softwood](https://en.wikipedia.org/wiki/Softwood "null")

[Hardwood](https://en.wikipedia.org/wiki/Hardwood "null")

[MDF](https://en.wikipedia.org/wiki/Medium-density_fibreboard "null")

#### 8.5.4. Elastomers

[Natural Rubber](https://en.wikipedia.org/wiki/Natural_rubber "null")

[TPU ](https://en.wikipedia.org/wiki/Thermoplastic_polyurethane "null")

[Silicone](https://en.wikipedia.org/wiki/Silicone "null")

#### 8.5.5. Ceramics

[Geopolymers](https://en.wikipedia.org/wiki/Geopolymer "null")

[Ceramics](https://en.wikipedia.org/wiki/Ceramic "null")

[Clay](https://en.wikipedia.org/wiki/Clay "null")

#### 8.5.6. Electronics

[PCBs](https://en.wikipedia.org/wiki/Polychlorinated_biphenyl "null")

[Electronic
Components](https://en.wikipedia.org/wiki/Electronic_component "null")

#### 8.5.7. Others

[Textiles](https://en.wikipedia.org/wiki/Textile "null")

[Leather](https://en.wikipedia.org/wiki/Leather "null")

[Concrete](https://en.wikipedia.org/wiki/Concrete "null")

[Rock](https://en.wikipedia.org/wiki/Rock_(geology) "null")

[Soil](https://en.wikipedia.org/wiki/Soil "null")

[Composite
Materials](https://en.wikipedia.org/wiki/Composite_material "null")

[Food](https://en.wikipedia.org/wiki/Food "null")

[Compost](https://en.wikipedia.org/wiki/Compost "null")

[Resin](https://en.wikipedia.org/wiki/Resin "null")

[Glass](https://en.wikipedia.org/wiki/Glass "null")

[Carbon
Fiber](https://en.wikipedia.org/wiki/Carbon_fiber_reinforced_polymer "null")

[Cardboard](https://en.wikipedia.org/wiki/Cardboard "null")

[Paper](https://en.wikipedia.org/wiki/Paper "null")

## 9. Record Data Properties

This class incorporates properties relating to record data. By "record
data" we mean information about who created the data and how up to date
it is. In highly dynamic environments, datasets can quickly become
obsolete and so it can be helpful to share information about the
provenance of the data.

![](https://assets.pubpub.org/yrp7hctn/51641401818620.png){#n8qz3t4kmpp}

### 9.1. Date Created

**Defintion: **Date record was created.

**Format: **Recommended practice is to use [ISO
8601](https://www.iso.org/iso-8601-date-and-time-format.html "null"),
i.e the format `YYYY-MM-DD`.

### 9.2. Created By

**Definition:**[Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") who
created the resource.

**Format: **Use [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

### 9.3. Last Updated

**Definition: **Date the record was updated.

**Format: **Recommended practice is to use [ISO
8601](https://www.iso.org/iso-8601-date-and-time-format.html "null"),
i.e the format `YYYY-MM-DD`.

### 9.4. Updated By

**Defintion: **The Agent who updated the record.

**Format: **Use
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.

### 9.5. Date Verified

**Definition: **Date the data in the record was verified.

**Format: **Recommended practice is to use [ISO
8601](https://www.iso.org/iso-8601-date-and-time-format.html "null"),
i.e. the format `YYYY-MM-DD`.

### 9.6. Verified By

**Defintion: **The agent who verified the data in the record.

**Format: **Use
the [Agent](https://standards.internetofproduction.org/pub/okw#agent-properties "null") class.