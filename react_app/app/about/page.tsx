'use client'

import Header from '@/components/Header'
import Footer from '@/components/Footer'

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      <main className="flex-1 px-8 py-16 flex flex-col items-center text-center gap-8">
        <h1 className="text-4xl font-bold text-text-primary">
          About AI Blog Writer
        </h1>
        <p className="max-w-3xl text-text-secondary text-lg leading-relaxed">
          AI Blog Writer helps you transform loose ideas into polished, publish-ready blog posts.
          Start with a keyword or topic, review the AI-generated outline, and generate a complete
          article tailored to your voice. Built for marketers, entrepreneurs, and creators who need
          to ship content faster without sacrificing quality. Our platform combines the power of AI
          with thoughtful editorial controls so you can move from concept to publication without the
          usual bottlenecks.
        </p>

        <section className="max-w-3xl text-left space-y-6 text-text-secondary leading-relaxed">
          <div>
            <h2 className="text-2xl font-semibold text-text-primary mb-2 text-center md:text-left">
              Why We Built It
            </h2>
            <p>
              Great content drives growth, but producing it consistently is hard. We built AI Blog Writer
              to reimagine the content workflow for small teams that don’t have time for lengthy research
              cycles. By combining SEO insights, outline generation, and long-form drafting in one place,
              we reduce the friction between having an idea and delivering a finished article.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-text-primary mb-2 text-center md:text-left">
              What You Can Do
            </h2>
            <ul className="space-y-3 list-disc list-inside">
          <li>Generate content plans backed by keyword research insights.</li>
          <li>Customize every section before committing to a full draft.</li>
          <li>Produce long-form content that is structured, readable, and on brand.</li>
              <li>Collaborate with teammates by sharing plans and iterating before publication.</li>
              <li>Export final drafts into your CMS with clean formatting and suggested imagery.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-text-primary mb-2 text-center md:text-left">
              Designed For Real Workflows
            </h2>
            <p>
              AI Blog Writer fits neatly into your existing publishing routine. Start with a quick draft,
              refine it with human insight, and hand it off to stakeholders with zero friction. Whether
              you are creating content calendars, product updates, or evergreen guides, our tools help
              you stay organized and on schedule.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-text-primary mb-2 text-center md:text-left">
              Our Promise
            </h2>
            <p>
              We believe that AI should amplify your voice, not replace it. That’s why every feature we
              build keeps the creator in control—from editing outlines to adjusting tone. We’re committed
              to transparent workflows, secure data handling, and a product roadmap shaped by the writers
              and marketers who rely on us every day.
            </p>
          </div>
        </section>
      </main>

      <section className="px-8 pb-6 text-center text-text-secondary text-sm">
        Crafted with care by{' '}
        <a
          href="https://github.com/RMartires"
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:underline"
        >
          Rohit Martires (@RMartires)
        </a>
        .
      </section>

      <Footer />
    </div>
  )
}

