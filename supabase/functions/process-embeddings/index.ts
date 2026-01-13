import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )
  
  // Get pending embedding jobs
  const { data: jobs } = await supabase
    .from('embedding_queue')
    .select('*')
    .eq('status', 'pending')
    .order('priority', { ascending: true })
    .limit(10)
  
  if (!jobs || jobs.length === 0) {
    return new Response(
      JSON.stringify({ processed: 0, message: 'No pending jobs' }),
      { headers: { 'Content-Type': 'application/json' } }
    )
  }
  
  let processed = 0
  let failed = 0
  
  for (const job of jobs) {
    try {
      // Mark as processing
      await supabase
        .from('embedding_queue')
        .update({ status: 'processing' })
        .eq('id', job.id)
      
      // Get record content based on table name
      const { data: record } = await supabase
        .from(job.table_name)
        .select('*')
        .eq('id', job.record_id)
        .single()
      
      if (!record) {
        throw new Error(`Record not found: ${job.table_name}.${job.record_id}`)
      }
      
      // Combine relevant text fields based on table
      let text = ''
      if (job.table_name === 'internal_resources') {
        text = [
          record.name,
          record.description,
          record.rate_notes
        ].filter(Boolean).join(' ')
      } else if (job.table_name === 'external_resources') {
        text = [
          record.vendor_name,
          record.description,
          record.pricing_notes
        ].filter(Boolean).join(' ')
      } else if (job.table_name === 'policies') {
        text = [
          record.policy_name,
          record.description,
          record.requirements
        ].filter(Boolean).join(' ')
      } else if (job.table_name === 'experience') {
        text = [
          record.description,
          record.keywords?.join(' ') || ''
        ].filter(Boolean).join(' ')
      } else if (job.table_name === 'rfps') {
        text = [
          record.project_title,
          record.client_name,
          record.parsed_markdown
        ].filter(Boolean).join(' ')
      }
      
      if (!text) {
        throw new Error('No text content found for embedding')
      }
      
      // Generate embedding
      const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: text
        })
      })
      
      if (!embeddingResponse.ok) {
        const errorText = await embeddingResponse.text()
        throw new Error(`OpenAI API error: ${errorText}`)
      }
      
      const embeddingData = await embeddingResponse.json()
      const embedding = embeddingData.data[0].embedding
      
      // Update record with embedding
      await supabase
        .from(job.table_name)
        .update({ embedding })
        .eq('id', job.record_id)
      
      // Mark job as completed
      await supabase
        .from('embedding_queue')
        .update({ 
          status: 'completed',
          processed_at: new Date().toISOString()
        })
        .eq('id', job.id)
      
      processed++
      
    } catch (error) {
      console.error(`Error processing job ${job.id}:`, error)
      
      // Mark job as failed
      await supabase
        .from('embedding_queue')
        .update({ 
          status: 'failed',
          error_message: error.message,
          retry_count: (job.retry_count || 0) + 1
        })
        .eq('id', job.id)
      
      failed++
    }
  }
  
  return new Response(
    JSON.stringify({ 
      processed, 
      failed,
      total: jobs.length 
    }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
