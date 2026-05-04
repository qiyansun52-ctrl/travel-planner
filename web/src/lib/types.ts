export interface UserPreferences {
  destination: string
  departureCity: string
  departureDate: string
  days: number
  totalBudget: number
  accommodationDescription: string
  experienceDescription: string
}

export type CardSection = "experience" | "transport" | "food"

export interface AttractionCard {
  id: string
  name: string
  section: CardSection
  description: string
  estimatedCost: string   // e.g. "¥50–100" or "免费"
  imageUrl: string        // may be empty string — UI shows emoji fallback
  tags: string[]
}

export interface DiscoverSections {
  experience: AttractionCard[]
  transport: AttractionCard[]
  food: AttractionCard[]
}

export interface Activity {
  id: string
  time: string
  endTime?: string
  place: string
  description: string
  type: "attraction" | "food" | "transport" | "hotel" | "free"
  estimatedCost?: number
  tips?: string
}

export interface DayPlan {
  day: number
  date: string
  title: string
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
  selectedAttractions: AttractionCard[]
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
