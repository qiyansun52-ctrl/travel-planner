export interface UserPreferences {
  destination: string
  departureCity: string
  departureDate: string      // ISO date string "2026-05-10"
  days: number
  totalBudget: number        // CNY
  accommodationDescription: string   // free text e.g. "森林小木屋，有壁炉"
  experienceDescription: string      // free text e.g. "当地人才知道的小馆子"
}

export interface Activity {
  id: string
  time: string               // "09:00"
  endTime?: string           // "11:00"
  place: string
  description: string
  type: "attraction" | "food" | "transport" | "hotel" | "free"
  estimatedCost?: number     // CNY
  tips?: string
}

export interface DayPlan {
  day: number
  date: string               // "2026-05-10"
  title: string              // e.g. "抵达 + 豫园探索"
  activities: Activity[]
  totalCost: number
}

export interface BudgetBreakdown {
  transport: number
  accommodation: number
  food: number
  attractions: number
  other: number
  total: number
}

export interface TravelPlan {
  id: string
  preferences: UserPreferences
  days: DayPlan[]
  budget: BudgetBreakdown
  tips: string[]
  createdAt: string
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  timestamp: string
}
