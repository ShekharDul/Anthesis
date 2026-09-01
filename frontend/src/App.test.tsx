import "@testing-library/jest-dom/vitest"
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { App } from "./App"

describe("App", () => {
  it("introduces Anthesis", () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "Music, grown into form." })).toBeVisible()
  })
})
