import { SearchForm } from "@/components/search/SearchForm"

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-50 flex flex-col items-center justify-center px-4 py-16">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          去哪儿？
        </h1>
        <p className="text-gray-500 text-lg">
          告诉 AI 你的旅行想法，它来帮你变成清晰的计划
        </p>
      </div>
      <SearchForm />
    </main>
  )
}
