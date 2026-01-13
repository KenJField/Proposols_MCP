import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const url = new URL(req.url)
  
  // Handle GET request - show form
  if (req.method === 'GET') {
    const token = url.pathname.split('/').pop()
    
    if (!token) {
      return new Response('Token required', { status: 400 })
    }
    
    // Validate token and get validation request
    const validation = await getValidationByToken(token)
    
    if (!validation) {
      return new Response('Invalid or expired validation link', { status: 404 })
    }
    
    // Return HTML form
    return new Response(createValidationForm(validation, token), {
      headers: { 'Content-Type': 'text/html' }
    })
  }
  
  // Handle POST request - process form submission
  if (req.method === 'POST') {
    const formData = await req.formData()
    const token = formData.get('token') as string
    const approval_status = formData.get('approval_status') as string
    const corrections = formData.get('corrections') as string
    
    if (!token) {
      return new Response('Token required', { status: 400 })
    }
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    const validation = await getValidationByToken(token)
    
    if (!validation) {
      return new Response('Invalid or expired validation link', { status: 404 })
    }
    
    // Update validation
    await supabase
      .from('validation_requests')
      .update({
        validation_status: approval_status,
        response_received_at: new Date().toISOString(),
        corrections_provided: corrections,
        response_data: {
          approval_status,
          corrections,
          submitted_at: new Date().toISOString()
        }
      })
      .eq('id', validation.id)
    
    // Create experience if corrections provided
    if (corrections && corrections.trim() !== '') {
      // Generate embedding
      const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: corrections
        })
      })
      
      if (embeddingResponse.ok) {
        const embeddingData = await embeddingResponse.json()
        
        // Extract keywords
        const keywords = corrections
          .toLowerCase()
          .split(/\s+/)
          .filter(w => w.length > 4)
          .slice(0, 10)
        
        // Create experience entry
        const { data: experience } = await supabase
          .from('experience')
          .insert({
            tenant_id: validation.tenant_id,
            description: `Validation correction: ${corrections}`,
            keywords,
            entity_type: validation.entity_type,
            entity_id: validation.entity_id,
            source_type: 'validation_response',
            source_id: validation.id,
            confidence_score: 0.95,
            embedding: embeddingData.data[0].embedding,
            created_by: 'ai'
          })
          .select()
          .single()
        
        if (experience) {
          // Link experience to validation
          await supabase
            .from('validation_requests')
            .update({
              experience_created: true,
              experience_id: experience.id
            })
            .eq('id', validation.id)
        }
      }
    }
    
    // Return success page
    return new Response(createSuccessPage(), {
      headers: { 'Content-Type': 'text/html' }
    })
  }
  
  return new Response('Method not allowed', { status: 405 })
})

async function getValidationByToken(token: string) {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )
  
  // Lookup validation by message_id (which stores the token)
  const { data } = await supabase
    .from('validation_requests')
    .select('*')
    .eq('message_id', token)
    .single()
  
  return data
}

function createValidationForm(validation: any, token: string): string {
  const currentInfo = validation.current_information || {}
  const infoHtml = Object.entries(currentInfo)
    .filter(([key]) => !['id', 'tenant_id', 'embedding', 'search_vector'].includes(key))
    .map(([key, value]) => `<tr><td><strong>${key.replace(/_/g, ' ')}</strong></td><td>${value}</td></tr>`)
    .join('')
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Validation Response</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #667eea; }
            .info-box {
                background: #f9f9f9;
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            table td {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            label {
                display: block;
                margin: 15px 0 5px 0;
                font-weight: bold;
            }
            textarea {
                width: 100%;
                min-height: 100px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: Arial, sans-serif;
            }
            .radio-group {
                margin: 10px 0;
            }
            .radio-group label {
                display: inline;
                font-weight: normal;
                margin-left: 5px;
            }
            button {
                background: #667eea;
                color: white;
                padding: 15px 40px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }
            button:hover {
                background: #5568d3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Validation Response</h1>
            <p><strong>Entity:</strong> ${validation.current_information?.name || 'Unknown'}</p>
            <p><strong>Question:</strong> ${validation.validation_question}</p>
            
            <div class="info-box">
                <h3>Current Information:</h3>
                <table>
                    ${infoHtml}
                </table>
            </div>
            
            <form method="POST">
                <input type="hidden" name="token" value="${token}">
                
                <label>Response:</label>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="approved" id="approved" checked>
                    <label for="approved">✅ Information is accurate</label>
                </div>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="updated" id="updated">
                    <label for="updated">⚠️ Needs corrections (see below)</label>
                </div>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="rejected" id="rejected">
                    <label for="rejected">❌ Cannot be allocated/approved</label>
                </div>
                
                <label for="corrections">Corrections or Additional Information:</label>
                <textarea name="corrections" id="corrections" placeholder="Please provide any corrections or additional information here..."></textarea>
                
                <button type="submit">Submit Response</button>
            </form>
        </div>
    </body>
    </html>
  `
}

function createSuccessPage(): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Response Submitted</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
                text-align: center;
            }
            .container {
                background: white;
                padding: 60px 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .checkmark {
                font-size: 80px;
                color: #4CAF50;
            }
            h1 { color: #333; }
            p { color: #666; font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>
            <h1>Thank You!</h1>
            <p>Your validation response has been submitted successfully.</p>
            <p>You can now close this window.</p>
        </div>
    </body>
    </html>
  `
}
