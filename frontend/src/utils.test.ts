import { describe, expect, it } from "vitest";
import { blankIntake, canGenerate } from "./utils";

describe("canGenerate", () => {
  it("requires a name and meaningful description", () => {
    expect(canGenerate(blankIntake)).toBe(false);
    expect(
      canGenerate({
        ...blankIntake,
        feature_name: "Routing",
        feature_description: "Route support requests using clear confidence thresholds.",
      }),
    ).toBe(true);
  });
});
