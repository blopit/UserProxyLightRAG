import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Progress } from '@/components/ui/Progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import ScopeSelector from '@/components/ScopeSelector'
import {
  validateSRN,
  listScopes,
  validateMigration,
  startMigration,
  getMigrationStatus,
  type ScopeContext,
  type MigrationPlan,
  type MigrationResponse
} from '@/api/lightrag'
import {
  Search,
  Plus,
  ArrowRight,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Database,
  Users,
  Project,
  MessageSquare,
  Tag
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface ScopeManagementProps {}

export const ScopeManagement: React.FC<ScopeManagementProps> = () => {
  const { t } = useTranslation()
  const [availableScopes, setAvailableScopes] = useState<ScopeContext[]>([])
  const [loadingScopes, setLoadingScopes] = useState(false)
  const [searchPattern, setSearchPattern] = useState('')
  const [selectedScope, setSelectedScope] = useState('')

  // Migration state
  const [migrationSource, setMigrationSource] = useState('')
  const [migrationTarget, setMigrationTarget] = useState('')
  const [migrationPlan, setMigrationPlan] = useState<MigrationPlan | null>(null)
  const [migrationStatus, setMigrationStatus] = useState<MigrationResponse | null>(null)
  const [migrationProgress, setMigrationProgress] = useState(0)
  const [loadingMigration, setLoadingMigration] = useState(false)

  // Load available scopes
  const loadScopes = useCallback(async () => {
    setLoadingScopes(true)
    try {
      const result = await listScopes(undefined, undefined, searchPattern || undefined, 100)
      setAvailableScopes(result.scopes)
    } catch (error) {
      console.error('Failed to load scopes:', error)
    } finally {
      setLoadingScopes(false)
    }
  }, [searchPattern])

  useEffect(() => {
    loadScopes()
  }, [loadScopes])

  // Validate migration plan
  const handleValidateMigration = async () => {
    if (!migrationSource || !migrationTarget) return

    setLoadingMigration(true)
    try {
      const plan = await validateMigration(migrationSource, migrationTarget)
      setMigrationPlan(plan)
    } catch (error) {
      console.error('Migration validation failed:', error)
      setMigrationPlan(null)
    } finally {
      setLoadingMigration(false)
    }
  }

  // Start migration
  const handleStartMigration = async () => {
    if (!migrationPlan) return

    setLoadingMigration(true)
    try {
      const response = await startMigration(migrationSource, migrationTarget, {
        dryRun: false,
        batchSize: 1000
      })
      setMigrationStatus(response)
      setMigrationProgress(0)

      // Start polling for status updates
      pollMigrationStatus(response.migration_id)
    } catch (error) {
      console.error('Migration failed to start:', error)
    } finally {
      setLoadingMigration(false)
    }
  }

  // Poll migration status
  const pollMigrationStatus = async (migrationId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const status = await getMigrationStatus(migrationId)
        setMigrationStatus(status)

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval)
          setMigrationProgress(100)
        } else if (status.status === 'running') {
          // Simulate progress - in real implementation this would come from the API
          setMigrationProgress(prev => Math.min(prev + 10, 90))
        }
      } catch (error) {
        console.error('Failed to poll migration status:', error)
        clearInterval(pollInterval)
      }
    }, 2000)
  }

  const getScopeDisplayName = (scope: ScopeContext) => {
    const c = scope.components
    const parts = [c.subject_type, c.subject_id]
    if (c.project) parts.push(`proj_${c.project}`)
    if (c.thread) parts.push(`thr_${c.thread}`)
    if (c.topic) parts.push(`top_${c.topic}`)
    return parts.join('.')
  }

  const getScopeIcon = (scope: ScopeContext) => {
    if (scope.components.topic) return <Tag className="h-4 w-4" />
    if (scope.components.thread) return <MessageSquare className="h-4 w-4" />
    if (scope.components.project) return <Project className="h-4 w-4" />
    return <Users className="h-4 w-4" />
  }

  const getDepthColor = (depth: number) => {
    switch (depth) {
      case 0: return 'bg-blue-100 text-blue-800'
      case 1: return 'bg-green-100 text-green-800'
      case 2: return 'bg-yellow-100 text-yellow-800'
      case 3: return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scope Management</h1>
          <p className="text-gray-600">Manage hierarchical data scopes and migration tools</p>
        </div>
      </div>

      <Tabs defaultValue="scopes" className="flex-1">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="scopes">Available Scopes</TabsTrigger>
          <TabsTrigger value="builder">Scope Builder</TabsTrigger>
          <TabsTrigger value="migration">Migration Tools</TabsTrigger>
        </TabsList>

        <TabsContent value="scopes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Available Scopes
              </CardTitle>
              <CardDescription>
                Browse and search through existing data scopes in the system
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input
                    placeholder="Search scopes (e.g., user.alice, proj_research)"
                    value={searchPattern}
                    onChange={(e) => setSearchPattern(e.target.value)}
                  />
                </div>
                <Button onClick={loadScopes} disabled={loadingScopes}>
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </div>

              {loadingScopes ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                </div>
              ) : (
                <div className="grid gap-3 max-h-96 overflow-y-auto">
                  {availableScopes.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      No scopes found. Try a different search pattern or check your scope system configuration.
                    </div>
                  ) : (
                    availableScopes.map((scope) => (
                      <div
                        key={scope.srn}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                      >
                        <div className="flex items-center gap-3">
                          {getScopeIcon(scope)}
                          <div>
                            <div className="font-medium">{getScopeDisplayName(scope)}</div>
                            <div className="text-xs text-gray-500 truncate max-w-md">
                              {scope.srn}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getDepthColor(scope.depth)}>
                            Depth {scope.depth}
                          </Badge>
                          <Badge variant="outline">
                            {scope.components.workspace.slice(0, 8)}...
                          </Badge>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="builder" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Scope Builder
              </CardTitle>
              <CardDescription>
                Build and validate new scope resource names (SRNs)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ScopeSelector
                value={selectedScope}
                onChange={setSelectedScope}
                placeholder="Build your scope (e.g., 1.abc123...def.user.alice.proj_research.thr_main.top_models)"
                showValidation={true}
                allowEmpty={true}
                className="w-full"
              />

              {selectedScope && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-2">
                      <div><strong>Valid SRN:</strong> {selectedScope}</div>
                      <div className="text-sm text-gray-600">
                        This scope can be used for scope-aware queries and operations
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <h4 className="font-medium mb-2">SRN Format</h4>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div><code>1.&lt;workspace&gt;.&lt;subject_type&gt;.&lt;subject_id&gt;</code></div>
                    <div><code>[.proj_&lt;project&gt;][.thr_&lt;thread&gt;][.top_&lt;topic&gt;]</code></div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Subject Types</h4>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div><Badge variant="secondary">user</Badge> - Human users</div>
                    <div><Badge variant="secondary">agent</Badge> - AI agents</div>
                    <div><Badge variant="secondary">system</Badge> - System processes</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="migration" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowRight className="h-5 w-5" />
                Workspace to Scope Migration
              </CardTitle>
              <CardDescription>
                Migrate data from workspace-based storage to scope-based hierarchical organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Source Workspace</label>
                  <Input
                    placeholder="Enter workspace ID (32-char hex)"
                    value={migrationSource}
                    onChange={(e) => setMigrationSource(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Target Scope</label>
                  <ScopeSelector
                    value={migrationTarget}
                    onChange={setMigrationTarget}
                    placeholder="Target scope SRN"
                    showValidation={false}
                    allowEmpty={false}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleValidateMigration}
                  disabled={!migrationSource || !migrationTarget || loadingMigration}
                >
                  Validate Migration
                </Button>
                {migrationPlan && (
                  <Button
                    onClick={handleStartMigration}
                    disabled={loadingMigration}
                    variant="default"
                  >
                    Start Migration
                  </Button>
                )}
              </div>

              {migrationPlan && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-2">
                      <div><strong>Migration Plan Validated</strong></div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>Estimated Items: {migrationPlan.estimated_items}</div>
                        <div>Estimated Time: {migrationPlan.estimated_time}</div>
                        <div>Storage Types: {migrationPlan.storage_types.join(', ')}</div>
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {migrationStatus && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Migration Status
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span>Status: {migrationStatus.status}</span>
                      {migrationStatus.status === 'completed' && <CheckCircle className="h-5 w-5 text-green-500" />}
                      {migrationStatus.status === 'failed' && <XCircle className="h-5 w-5 text-red-500" />}
                      {migrationStatus.status === 'running' && <Clock className="h-5 w-5 text-yellow-500" />}
                    </div>

                    {migrationStatus.status === 'running' && (
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Progress</span>
                          <span>{migrationProgress}%</span>
                        </div>
                        <Progress value={migrationProgress} />
                      </div>
                    )}

                    <div className="text-sm text-gray-600">
                      Migration ID: {migrationStatus.migration_id}
                    </div>

                    {migrationStatus.message && (
                      <div className="text-sm">
                        Message: {migrationStatus.message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ScopeManagement