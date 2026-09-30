import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { PasswordInput } from '@/components/password-input'
import { RoleBadge } from '@/components/status-badge'
import { Hint, PageHeader } from '@/components/feedback'
import { useAuth } from '@/lib/auth-context'
import { useMutation } from '@/hooks/use-async'
import { authApi, userApi } from '@/lib/endpoints'
import { Key } from '@/components/animate-ui/icons/key'
import { User } from '@/components/animate-ui/icons/user'
import { LogOut } from '@/components/animate-ui/icons/log-out'

export function SettingsPage() {
  const { user, logoutAll } = useAuth()
  const navigate = useNavigate()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const { run: changePassword, isPending, error } = useMutation(async () => {
    await userApi.changePassword({ current_password: currentPassword, new_password: newPassword })
    // The server revokes every session on a password change, including this
    // one, so the local session has to go too or the UI lies about being signed in.
    await logoutAll()
  })

  async function handlePasswordChange(event: React.FormEvent) {
    event.preventDefault()

    if (newPassword !== confirmPassword) {
      toast.error('The new passwords do not match')
      return
    }

    const result = await changePassword()
    if (!result) return

    toast.success('Password updated', { description: 'Please sign in again.' })
    navigate('/login', { replace: true })
  }

  async function handleSignOutEverywhere() {
    await authApi.logoutAll().catch(() => undefined)
    await logoutAll()
    toast.success('Signed out of all sessions')
    navigate('/login', { replace: true })
  }

  if (!user) return null

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Your account and active sessions." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User size={16} className="text-muted-foreground" />
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FieldGroup>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">Name</span>
                <span className="text-sm font-medium">{user.full_name}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">Email</span>
                <span className="truncate text-sm font-medium">{user.email}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">Phone</span>
                <span className="text-sm font-medium">{user.phone ?? '—'}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">Role</span>
                <RoleBadge role={user.role} />
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">Verified</span>
                <span className="text-sm font-medium">{user.is_verified ? 'Yes' : 'No'}</span>
              </div>
            </FieldGroup>

            <Hint>
              Profile details are edited by an administrator. Email verification is not part of
              this release.
            </Hint>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card id="password">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Key size={16} className="text-muted-foreground" />
                Change password
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="current_password">Current password</FieldLabel>
                    <PasswordInput
                      id="current_password"
                      name="current_password"
                      autoComplete="current-password"
                      required
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.target.value)}
                    />
                  </Field>

                  <Field>
                    <FieldLabel htmlFor="new_password">New password</FieldLabel>
                    <PasswordInput
                      id="new_password"
                      name="new_password"
                      autoComplete="new-password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                    />
                    <FieldDescription>
                      At least 8 characters with upper and lower case, a digit, and a symbol.
                    </FieldDescription>
                  </Field>

                  <Field>
                    <FieldLabel htmlFor="confirm_password">Confirm new password</FieldLabel>
                    <PasswordInput
                      id="confirm_password"
                      name="confirm_password"
                      autoComplete="new-password"
                      required
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                    />
                  </Field>

                  {error ? <FieldError>{error.message}</FieldError> : null}
                </FieldGroup>

                <Button type="submit" disabled={isPending}>
                  {isPending ? 'Updating…' : 'Update password'}
                </Button>
                <Hint>Changing your password signs you out everywhere, including this device.</Hint>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <Button variant="outline" onClick={handleSignOutEverywhere}>
                <LogOut size={15} />
                Sign out of all devices
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
