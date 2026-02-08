import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { FolderOpen } from "lucide-react"
import { PageEmptyState } from "./PageEmptyState"

function renderWithRouter(ui: React.ReactElement) {
  return render(ui, { wrapper: BrowserRouter })
}

describe("PageEmptyState", () => {
  it("renders icon, title, and description", () => {
    renderWithRouter(
      <PageEmptyState
        icon={FolderOpen}
        title="Тестовый заголовок"
        description="Тестовое описание"
      />
    )
    expect(screen.getByText("Тестовый заголовок")).toBeInTheDocument()
    expect(screen.getByText("Тестовое описание")).toBeInTheDocument()
  })

  it("renders action button when actionLabel and actionLink provided", () => {
    renderWithRouter(
      <PageEmptyState
        icon={FolderOpen}
        title="Заголовок"
        description="Описание"
        actionLabel="Перейти к импорту"
        actionLink="/import"
      />
    )
    const link = screen.getByRole("link", { name: "Перейти к импорту" })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/import")
  })

  it("does not render action button when actionLabel is missing", () => {
    renderWithRouter(
      <PageEmptyState
        icon={FolderOpen}
        title="Заголовок"
        description="Описание"
      />
    )
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("does not render action button when actionLink is missing", () => {
    renderWithRouter(
      <PageEmptyState
        icon={FolderOpen}
        title="Заголовок"
        description="Описание"
        actionLabel="Кнопка"
      />
    )
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })
})
