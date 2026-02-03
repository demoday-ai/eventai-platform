import * as React from "react"

interface SelectContextValue {
  value?: string
  onValueChange?: (value: string) => void
  items: React.ReactNode[]
  setItems: (items: React.ReactNode[]) => void
}

const SelectContext = React.createContext<SelectContextValue>({
  items: [],
  setItems: () => {},
})

interface SelectProps {
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
}

export function Select({ value, onValueChange, children }: SelectProps) {
  const [items, setItems] = React.useState<React.ReactNode[]>([])

  return (
    <SelectContext.Provider value={{ value, onValueChange, items, setItems }}>
      {children}
    </SelectContext.Provider>
  )
}

interface SelectTriggerProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  children?: React.ReactNode
}

export function SelectTrigger({ id, children, className, ...props }: SelectTriggerProps) {
  const { value, onValueChange, items } = React.useContext(SelectContext)

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onValueChange?.(e.target.value)}
      className={`flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${className || ""}`}
      {...props}
    >
      {items}
    </select>
  )
}

export function SelectValue({ placeholder: _placeholder }: { placeholder?: string }) {
  return null
}

interface SelectContentProps {
  children: React.ReactNode
}

export function SelectContent({ children }: SelectContentProps) {
  const { setItems } = React.useContext(SelectContext)

  React.useEffect(() => {
    const childArray = React.Children.toArray(children)
    setItems(childArray)
  }, [children, setItems])

  return null
}

interface SelectItemProps {
  value: string
  children: React.ReactNode
}

export function SelectItem({ value, children }: SelectItemProps) {
  return <option value={value}>{children}</option>
}
