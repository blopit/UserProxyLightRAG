import React, { useState, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { CheckCircle, XCircle, Search, Loader2 } from 'lucide-react'
import { validateSRN, listScopes, type ScopeContext, type SRNComponents } from '@/api/lightrag'
import { useDebounce } from '@/hooks/useDebounce'

interface ScopeSelectorProps {
  value?: string
  onChange?: (scope: string) => void
  placeholder?: string
  showValidation?: boolean
  allowEmpty?: boolean
  className?: string
}

export const ScopeSelector: React.FC<ScopeSelectorProps> = ({
  value = '',
  onChange,
  placeholder = 'Enter SRN (e.g., 1.abc123...def.user.alice.proj_research)',
  showValidation = true,
  allowEmpty = true,
  className = ''
}) => {
  const [inputValue, setInputValue] = useState(value)
  const [isValidating, setIsValidating] = useState(false)
  const [validation, setValidation] = useState<{
    valid: boolean
    components?: SRNComponents
    error?: string
  } | null>(null)
  const [availableScopes, setAvailableScopes] = useState<ScopeContext[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const debouncedValue = useDebounce(inputValue, 500)

  // Validate SRN when debounced value changes
  useEffect(() => {
    if (!debouncedValue && allowEmpty) {
      setValidation(null)
      onChange?.('')
      return
    }

    if (!debouncedValue) {
      setValidation({ valid: false, error: 'SRN is required' })
      return
    }

    const validateAsync = async () => {
      setIsValidating(true)
      try {
        const result = await validateSRN(debouncedValue)
        setValidation(result)
        if (result.valid) {
          onChange?.(debouncedValue)
        }
      } catch (error) {
        setValidation({
          valid: false,
          error: error instanceof Error ? error.message : 'Validation failed'
        })
      } finally {
        setIsValidating(false)
      }
    }

    validateAsync()
  }, [debouncedValue, allowEmpty, onChange])

  // Load available scopes for suggestions
  const loadScopes = useCallback(async () => {
    try {
      const result = await listScopes(undefined, undefined, undefined, 50)
      setAvailableScopes(result.scopes)
    } catch (error) {
      console.error('Failed to load scopes:', error)
    }
  }, [])

  useEffect(() => {
    loadScopes()
  }, [loadScopes])

  const handleInputChange = (newValue: string) => {
    setInputValue(newValue)
  }

  const handleScopeSelect = (selectedScope: string) => {
    setInputValue(selectedScope)
    setShowSuggestions(false)
  }

  const getScopeTypeLabel = (components: SRNComponents) => {
    const parts = [components.subject_type, components.subject_id]
    if (components.project) parts.push(`proj_${components.project}`)
    if (components.thread) parts.push(`thr_${components.thread}`)
    if (components.topic) parts.push(`top_${components.topic}`)
    return parts.join('.')
  }

  const getValidationIcon = () => {
    if (isValidating) {
      return <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
    }
    if (validation?.valid) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    }
    if (validation && !validation.valid) {
      return <XCircle className="h-4 w-4 text-red-500" />
    }
    return null
  }

  const filteredScopes = availableScopes.filter(scope =>
    scope.srn.toLowerCase().includes(inputValue.toLowerCase())
  ).slice(0, 10)

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="relative">
        <Input
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder={placeholder}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          className={`pr-10 ${
            validation?.valid ? 'border-green-500' :
            validation && !validation.valid ? 'border-red-500' : ''
          }`}
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          {getValidationIcon()}
        </div>

        {/* Scope suggestions dropdown */}
        {showSuggestions && filteredScopes.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
            {filteredScopes.map((scope) => (
              <div
                key={scope.srn}
                className="px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                onClick={() => handleScopeSelect(scope.srn)}
              >
                <div className="text-sm font-medium text-gray-900 truncate">
                  {getScopeTypeLabel(scope.components)}
                </div>
                <div className="text-xs text-gray-500 truncate">
                  {scope.srn}
                </div>
                <div className="flex gap-1 mt-1">
                  <Badge variant="secondary" className="text-xs">
                    Depth: {scope.depth}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {scope.components.workspace.slice(0, 8)}...
                  </Badge>
                </div>
              </div>
            ))}
            <div className="px-3 py-2 text-xs text-gray-500 bg-gray-50">
              <Search className="h-3 w-3 inline mr-1" />
              {filteredScopes.length} of {availableScopes.length} scopes shown
            </div>
          </div>
        )}
      </div>

      {/* Validation feedback */}
      {showValidation && validation && (
        <div>
          {validation.valid && validation.components ? (
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-700">
                <div className="space-y-1">
                  <div>Valid SRN</div>
                  <div className="text-xs space-y-1">
                    <div><strong>Workspace:</strong> {validation.components.workspace}</div>
                    <div><strong>Subject:</strong> {validation.components.subject_type}.{validation.components.subject_id}</div>
                    {validation.components.project && (
                      <div><strong>Project:</strong> {validation.components.project}</div>
                    )}
                    {validation.components.thread && (
                      <div><strong>Thread:</strong> {validation.components.thread}</div>
                    )}
                    {validation.components.topic && (
                      <div><strong>Topic:</strong> {validation.components.topic}</div>
                    )}
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          ) : validation.error ? (
            <Alert className="border-red-200 bg-red-50">
              <XCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-700">
                {validation.error}
              </AlertDescription>
            </Alert>
          ) : null}
        </div>
      )}

      {/* Quick scope builder */}
      <div className="text-xs text-gray-500">
        <details className="mt-2">
          <summary className="cursor-pointer hover:text-gray-700">Quick SRN Builder</summary>
          <div className="mt-2 p-3 border border-gray-200 rounded-md bg-gray-50 space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <strong>Format:</strong> 1.&lt;workspace&gt;.&lt;subject_type&gt;.&lt;subject_id&gt;[.proj_&lt;project&gt;][.thr_&lt;thread&gt;][.top_&lt;topic&gt;]
              </div>
              <div>
                <strong>Example:</strong> 1.abc123...def.user.alice.proj_research.thr_main.top_models
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div><strong>Subject Types:</strong> user, agent, system</div>
              <div><strong>Workspace:</strong> 32-char hex ID</div>
              <div><strong>Optional:</strong> project, thread, topic</div>
            </div>
          </div>
        </details>
      </div>
    </div>
  )
}

export default ScopeSelector