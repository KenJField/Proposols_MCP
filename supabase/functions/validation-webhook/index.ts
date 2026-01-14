import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  try {
    const payload = await req.json()
    
    // Validate webhook signature (important for security)
    const isValid = await validateTeamsWebhook(req.headers, payload)
    if (!isValid) {
      return new Response('Unauthorized', { status: 401 })
    }
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    // Extract validation response from Adaptive Card submission
    const { action, data } = payload.value || {}
    
    if (action?.verb === 'submit_validation') {
      const validation_id = data.validation_id
      const approval_status = data.approval_status
      const corrections = data.corrections
      
      // Store raw response data - AI will process it
      const { data: validation } = await supabase
        .from('validation_requests')
        .update({
          validation_status: approval_status === 'approved' ? 'approved' : 
                           approval_status === 'rejected' ? 'rejected' : 'updated',
          response_received_at: new Date().toISOString(),
          corrections_provided: corrections,
          response_data: {
            approval_status,
            corrections,
            responded_by: payload.from?.user?.displayName || 'Unknown',
            responded_at: new Date().toISOString()
          }
        })
        .eq('id', validation_id)
        .select()
        .single()
      
      if (!validation) {
        return new Response(
          JSON.stringify({ error: 'Validation request not found' }),
          { status: 404, headers: { 'Content-Type': 'application/json' } }
        )
      }
      
      return new Response(
        JSON.stringify({ 
          type: 'message',
          text: '✅ Thank you! Your validation response has been recorded. The AI will process your feedback.'
        }),
        { 
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }
      )
    }
    
    return new Response('OK', { status: 200 })
    
  } catch (error) {
    console.error('Webhook error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    )
  }
})

async function validateTeamsWebhook(headers: Headers, payload: any): Promise<boolean> {
  // Implement HMAC signature validation
  // See: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-outgoing-webhook
  const signature = headers.get('authorization')
  const hmac = Deno.env.get('TEAMS_WEBHOOK_SECRET')
  
  // Validate signature matches
  // Implementation depends on your Teams app setup
  // For production, implement proper HMAC validation
  return true  // Placeholder - implement proper validation
}
