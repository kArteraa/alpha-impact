import type { ClientProfile, Feature } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { Route } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FEATURES } from "../data/profile";
import { TEST_CLIENT, renderWithCompany, stubApi } from "../testing";
import { ProfilePage } from "./ProfilePage";

const UPDATED = "2026-10-01T00:00:00Z";
const PROFILE_URL = `/api/profile/${TEST_CLIENT}`;
const PATCH_URL = `PATCH ${PROFILE_URL}/features/industry_class`;

function feature(value: Feature["value"], source: Feature["source"]): Feature {
  return { value, source, confidence: source === "bank" ? 1 : 0.7, updated_at: UPDATED };
}

function profile(industry: Feature): ClientProfile {
  return {
    client_id: TEST_CLIENT,
    group_id: "group_1_sb",
    group_members: [],
    exposures: {},
    flags: {},
    version: 1,
    features: {
      okved_name: feature("Торговля оптовая неспециализированная", "bank"),
      region: feature("Самарская область", "bank"),
      revenue_rub: feature(18_500_000_000, "bank"),
      import_countries: feature(["КИТАЙ", "ТУРЦИЯ"], "bank"),
      industry_class: industry,
    },
  };
}

const LOADED = profile(feature("wholesale", "inferred"));

function renderProfile(retry = vi.fn()) {
  renderWithCompany(<ProfilePage />, {
    path: "/profile",
    routes: <Route path="/" element={<h1>Главный экран</h1>} />,
    feed: { retry },
  });
  return retry;
}

function choose(scope: HTMLElement, option: string) {
  fireEvent.click(within(scope).getByRole("combobox", { name: "Отрасль" }));
  fireEvent.click(within(scope).getByRole("option", { name: option }));
}

async function card(label: string) {
  return screen.findByRole("listitem", { name: label });
}

describe("ProfilePage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows what the bank knows about the company", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED] });
    renderProfile();

    expect(within(await card("Отрасль")).getByText("Оптовая торговля")).toBeTruthy();
    expect(within(await card("Регион")).getByText("Самарская область")).toBeTruthy();
    expect(within(await card("Страны импорта")).getByText("КИТАЙ, ТУРЦИЯ")).toBeTruthy();
    expect(within(await card("Выручка")).getByText(/18\s500\s000\s000/)).toBeTruthy();
  });

  it("splits the features into titled groups", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED] });
    renderProfile();
    await card("Отрасль");

    const groups = screen.getAllByRole("region").map((group) => group.querySelector("h2")?.textContent);
    expect(groups).toEqual(["Компания", "География", "Масштаб"]);
  });

  it("keeps bank facts read-only", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED] });
    renderProfile();

    const region = await card("Регион");
    expect(within(region).getByText("по данным банка")).toBeTruthy();
    expect(within(region).queryByRole("button", { name: "Изменить" })).toBeNull();
  });

  it("corrects the derived industry through the API", async () => {
    const fetchMock = stubApi({
      [`GET ${PROFILE_URL}`]: [200, LOADED],
      [PATCH_URL]: [200, profile(feature("logistics", "user"))],
    });
    renderProfile();
    const industry = await card("Отрасль");
    expect(within(industry).getByText("определено по данным")).toBeTruthy();

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    choose(industry, "Логистика");
    fireEvent.click(within(industry).getByRole("button", { name: "Сохранить" }));

    expect(await within(industry).findByText("Логистика")).toBeTruthy();
    expect(within(industry).getByText("изменено вами")).toBeTruthy();
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ value: "logistics" });
  });

  it("rebuilds the feed once the corrected profile is saved", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED], [PATCH_URL]: [200, profile(feature("logistics", "user"))] });
    const retry = renderProfile();
    const industry = await card("Отрасль");

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    choose(industry, "Логистика");
    fireEvent.click(within(industry).getByRole("button", { name: "Сохранить" }));

    expect(await within(industry).findByText("изменено вами")).toBeTruthy();
    expect(retry).toHaveBeenCalledOnce();
  });

  it("drops an edit on cancel", async () => {
    const fetchMock = stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED] });
    renderProfile();
    const industry = await card("Отрасль");

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    choose(industry, "Розничная торговля");
    fireEvent.click(within(industry).getByRole("button", { name: "Отмена" }));

    expect(within(industry).getByText("Оптовая торговля")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("says why a correction was not saved", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED], [PATCH_URL]: [404, "unknown industry"] });
    const retry = renderProfile();
    const industry = await card("Отрасль");

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    fireEvent.click(within(industry).getByRole("button", { name: "Сохранить" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Не удалось сохранить (404)");
    expect(retry).not.toHaveBeenCalled();
  });

  it("saves the option shown in the list when the industry is unknown", async () => {
    const fetchMock = stubApi({
      [`GET ${PROFILE_URL}`]: [200, profile(feature(null, "inferred"))],
      [PATCH_URL]: [200, profile(feature("wholesale", "user"))],
    });
    renderProfile();
    const industry = await card("Отрасль");

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    const shown = within(industry).getByRole("combobox", { name: "Отрасль" }).textContent;
    fireEvent.click(within(industry).getByRole("button", { name: "Сохранить" }));

    expect(await within(industry).findByText("изменено вами")).toBeTruthy();
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    const { value } = JSON.parse(String(patch?.[1]?.body));
    expect(shown).toBe(FEATURES.industry_class.labels?.[value]);
  });

  it("sends one correction for a double click", async () => {
    const fetchMock = stubApi({
      [`GET ${PROFILE_URL}`]: [200, LOADED],
      [PATCH_URL]: [200, profile(feature("logistics", "user"))],
    });
    renderProfile();
    const industry = await card("Отрасль");

    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    const save = within(industry).getByRole("button", { name: "Сохранить" });
    fireEvent.click(save);
    fireEvent.click(save);
    await within(industry).findByText("изменено вами");

    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH").length).toBe(1);
  });

  it("drops the save error when the edit is cancelled", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED], [PATCH_URL]: [403, "read-only"] });
    renderProfile();
    const industry = await card("Отрасль");
    fireEvent.click(within(industry).getByRole("button", { name: "Изменить" }));
    fireEvent.click(within(industry).getByRole("button", { name: "Сохранить" }));
    await screen.findByRole("alert");

    fireEvent.click(within(industry).getByRole("button", { name: "Отмена" }));

    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("explains a company the bank has no card for", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, { ...LOADED, features: {} }] });
    renderProfile();

    expect(await screen.findByText("Данных о компании у банка нет")).toBeTruthy();
  });

  it("says so when the profile cannot be loaded", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [500, "boom"] });
    renderProfile();

    expect((await screen.findByRole("alert")).textContent).toBe("Не удалось загрузить профиль");
  });

  it("confirms the profile and opens the main screen", async () => {
    stubApi({ [`GET ${PROFILE_URL}`]: [200, LOADED] });
    renderProfile();
    await card("Отрасль");

    fireEvent.click(screen.getByRole("button", { name: "Всё верно" }));

    expect(await screen.findByRole("heading", { name: "Главный экран" })).toBeTruthy();
  });
});
