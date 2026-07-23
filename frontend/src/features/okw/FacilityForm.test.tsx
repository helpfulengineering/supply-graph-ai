import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { FacilityForm } from "./FacilityForm";

const authState = { hasWrite: true };
const reportAuthFailure = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: authState.hasWrite,
    reportAuthFailure,
  }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

function renderForm(mode: "create" | "edit" = "create") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <FacilityForm
          mode={mode}
          facilityId={mode === "edit" ? "okw-1" : undefined}
          initialFacility={
            mode === "edit"
              ? {
                  id: "okw-1",
                  name: "Laser Fab Lab",
                  facility_status: "Active",
                  access_type: "Membership",
                  location: {
                    city: "Austin",
                    country: "US",
                    address: { city: "Austin", country: "US", region: "TX" },
                  },
                  manufacturing_processes: ["laser_cutting"],
                }
              : undefined
          }
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FacilityForm", () => {
  beforeEach(() => {
    authState.hasWrite = true;
    reportAuthFailure.mockClear();
    navigate.mockClear();
  });

  it("disables save and shows write-gate when user lacks write", async () => {
    authState.hasWrite = false;
    renderForm("create");
    expect(
      await screen.findByText(/Connect a write-capable API key to save/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create facility/i })).toBeDisabled();
  });

  it("validates then creates and navigates to detail", async () => {
    const user = userEvent.setup();
    let validateBody: unknown;
    let createBody: unknown;
    server.use(
      http.post("*/v1/api/okw/validate", async ({ request }) => {
        validateBody = await request.json();
        return HttpResponse.json({
          is_valid: true,
          score: 1,
          errors: [],
          warnings: [],
          suggestions: [],
        });
      }),
      http.post("*/v1/api/okw/create", async ({ request }) => {
        createBody = await request.json();
        return HttpResponse.json(
          {
            success: true,
            message: "created",
            okw: { id: "okw-created", name: "Test Lab" },
          },
          { status: 201 },
        );
      }),
    );

    renderForm("create");
    await screen.findByLabelText(/3D Printing/i);

    await user.type(screen.getByLabelText(/^Name/i), "Test Lab");
    await user.type(screen.getByLabelText(/^City/i), "Austin");
    await user.type(screen.getByLabelText(/^Country/i), "US");
    await user.click(screen.getByLabelText(/3D Printing/i));
    await user.click(screen.getByRole("button", { name: /Create facility/i }));

    await waitFor(() => {
      expect(validateBody).toBeTruthy();
      expect(createBody).toBeTruthy();
      expect(navigate).toHaveBeenCalledWith("/facilities/okw-created?created=1");
    });

    const content = (validateBody as { content: Record<string, unknown> }).content;
    expect(content.name).toBe("Test Lab");
    expect(content.manufacturing_processes).toContain("3d_printing");
  });

  it("blocks save when validation fails", async () => {
    const user = userEvent.setup();
    const createSpy = vi.fn();
    server.use(
      http.post("*/v1/api/okw/validate", () =>
        HttpResponse.json({
          is_valid: false,
          score: 0.2,
          errors: [{ message: "location incomplete" }],
          warnings: [],
          suggestions: [],
        }),
      ),
      http.post("*/v1/api/okw/create", () => {
        createSpy();
        return HttpResponse.json({ okw: { id: "x" } }, { status: 201 });
      }),
    );

    renderForm("create");
    await screen.findByLabelText(/Laser Cutting/i);
    await user.type(screen.getByLabelText(/^Name/i), "Bad Lab");
    await user.type(screen.getByLabelText(/^City/i), "Austin");
    await user.type(screen.getByLabelText(/^Country/i), "US");
    await user.click(screen.getByRole("button", { name: /Create facility/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Validation failed/i);
    expect(createSpy).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });
});
