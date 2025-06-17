import {
  S3Client,
  paginateListObjectsV2,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import * as YAML from 'yaml'

export class Atom {
  constructor(readonly identifier: string, readonly description?: string, readonly link?: string) {}

  toString() {
    return this.description
      ? `${this.description} (${this.identifier})`
      : this.identifier;
  }
}

export function parseAtom(atom: any): Atom | undefined {
  if (typeof atom !== "object") { return; }

  const identifier = atom["identifier"] as string | undefined;
  const description = atom["description"] as string | undefined;
  const link = atom["link"] as string | undefined;

  return identifier ? new Atom(identifier, description, link) : undefined;
}

export function parseAtomArray(atom: any) {
  return Array.isArray(atom)
    ? atom.map(parseAtom).filter(<T>(value: T | null | undefined): value is T => { return !!value; })
    : [];
}

export interface OkwParty {
  title: string;
  supplies?: Atom[];
  tools?: Atom[];
  inventory?: Atom[];
}

export function parseOKW(body: string): OkwParty {
  const yaml = YAML.parse(body);
  const title = yaml["title"] as string | undefined;
  if (typeof title !== "string") { throw new Error("Title must be a string"); }
  const supplies = parseAtomArray(yaml["supply-atoms"]);
  const tools = parseAtomArray(yaml["tool-list-atoms"])
  const inventory = parseAtomArray(yaml["inventory-atoms"])
  return { title, supplies, tools, inventory };
}

export interface OkhDesign {
  title: string;
  product: Atom;
  bom?: Atom[];
  tools?: Atom[];
  bomOutput?: Atom[];
}

export function parseOKH(body: string): OkhDesign | undefined {
  const yml = YAML.parse(body);
  const title = yml["title"];
  if (typeof title !== "string") { return; }

  const product = parseAtom(yml["product-atom"])
  if (!product) { return; }
  const bom = parseAtomArray(yml["bom-atoms"])
  const tools = parseAtomArray(yml["tool-list-atoms"])
  const bomOutput = parseAtomArray(yml["bom-output-atoms"])
  return { title, product, bom, tools, bomOutput };
}

export interface SupplyTree {
  readonly product: Atom;
  print(indent: number): void;
}

export class SuppliedSupplyTree implements SupplyTree {

  constructor(readonly supplier: OkwParty, readonly product: Atom) { }

  print(indent: number): void {
    console.log(`${" ".repeat(indent)}Supplier: ${this.supplier.title}/${this.product}`);
  }
}

export class InventorySupplyTree implements SupplyTree {
  constructor(readonly maker: OkwParty, readonly product: Atom) { }

  print(indent: number): void {
    console.log(`${" ".repeat(indent)}Maker Inventory: ${this.maker.title}/${this.product}`);
  }
}

export class MadeSupplyTree implements SupplyTree {
  constructor(readonly product: Atom, readonly design: OkhDesign, readonly maker: OkwParty, readonly supplies: readonly SupplyTree[]) { }
  print(indent: number): void {
    console.log(`${" ".repeat(indent)}Maker: ${this.maker.title}/${this.design.title}`);
    for (const supply of this.supplies) {
      supply.print(indent + 2);
    }
  }
}

export class MissingSupplyTree implements SupplyTree {
  constructor(readonly product: Atom) { }
  print(indent: number): void {
    console.log(`${" ".repeat(indent)}Missing: ${this.product}`);
  }
}


export function* supplyTreeQuery(product: Atom, parties: readonly OkwParty[], designs: readonly OkhDesign[]) {
  let found = false;
  for (const supplier of parties) {
    if (supplier.supplies?.some(s => s.identifier === product.identifier)) {
      found = true;
      yield new SuppliedSupplyTree(supplier, product);
    }
  }

  for (const design of designs.filter(d => d.product.identifier === product.identifier)) {
    for (const maker of parties) {
      if (compatible(maker, design)) {
        found = true;

        const bomTrees = new Array<SupplyTree>();
        for (const bomItem of design.bom ?? []) {
          if (maker.inventory?.some(i => i.identifier === bomItem.identifier)) {
            bomTrees.push(new InventorySupplyTree(maker, bomItem));
          } else {
            bomTrees.push(...supplyTreeQuery(bomItem, parties, designs));
          }
        }

        yield new MadeSupplyTree(product, design, maker, bomTrees);
      }
    }

    if (!found) {
      yield new MissingSupplyTree(product);
    }
  }

  function compatible({ tools: makerTools }: OkwParty, { tools: requiredTools }: OkhDesign): boolean {
    if (!makerTools || makerTools.length === 0) { return false; }
    if (!requiredTools || requiredTools.length === 0) { return true; }
    return requiredTools.every(tool => makerTools.some(t => t.identifier === tool.identifier));
  }
}


async function main() {
  const s3Client = new S3Client({
    region: "us-east-1",
    // https://github.com/aws/aws-sdk-js-v3/issues/2321#issuecomment-916336230
    signer: { sign: (request) => Promise.resolve(request) }
  })
  const bucketName = "github-helpfulengineering-library"

  async function* listFiles(prefix: string) {
    const paginator = paginateListObjectsV2(
      { client: s3Client },
      { Bucket: bucketName, Delimiter: "/", Prefix: prefix }
    );

    for await (const page of paginator) {
      for (const object of page.Contents ?? []) {
        // console.log(object.Key);
        yield object;
      }
    }
  }

  async function getObject(key: string) {
    const response = await s3Client.send(new GetObjectCommand({ Bucket: bucketName, Key: key }));
    return await response.Body?.transformToString();
  }

  try {
    const okws = new Array<OkwParty>();
    for await (const file of listFiles("beta/okw/")) {
      if (!file.Key) { continue; }
      const body = await getObject(file.Key);
      const okw = body ? parseOKW(body) : undefined;
      if (okw) { okws.push(okw); }
    }

    const okhs = new Array<OkhDesign>();
    for await (const file of listFiles("beta/okh/")) {
      if (!file.Key) { continue; }
      const body = await getObject(file.Key);
      const okh = body ? parseOKH(body) : undefined;
      if (okh) { okhs.push(okh); }
    }

    const results = supplyTreeQuery(okhs[0].product, okws, okhs);
    for (const result of results) {
      result.print(0);
    }

    // console.log(JSON.stringify(okws, undefined, 4));
    // console.log(JSON.stringify(okhs, undefined, 4));
  } finally {
    s3Client.destroy();
  }
}

main().catch(console.error);