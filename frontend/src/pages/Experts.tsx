import { useState, useEffect } from "react"
import { APP_NAME } from "../lib/constants"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs"
import { ExpertMatchingTab } from "./ExpertMatching"
import { ExpertListTab } from "./ExpertList"
import { CoverageTab } from "./Coverage"

export function Experts() {
  const [activeTab, setActiveTab] = useState("matching")

  useEffect(() => {
    document.title = `${APP_NAME} - Эксперты`
  }, [])

  return (
    <div className="grid gap-6">
      <h2 className="text-2xl font-bold">Эксперты</h2>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="matching">Матчинг</TabsTrigger>
          <TabsTrigger value="list">Список</TabsTrigger>
          <TabsTrigger value="coverage">Покрытие</TabsTrigger>
        </TabsList>
        <TabsContent value="matching">
          <ExpertMatchingTab onSwitchTab={setActiveTab} />
        </TabsContent>
        <TabsContent value="list">
          <ExpertListTab />
        </TabsContent>
        <TabsContent value="coverage">
          <CoverageTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
