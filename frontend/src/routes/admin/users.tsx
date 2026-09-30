import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/password-input'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { RoleBadge } from '@/components/status-badge'
import { EmptyState, ErrorState, PageHeader } from '@/components/feedback'
import { OrbPanel } from '@/components/orb-loader'
import { useAsync, useDebounced, useMutation } from '@/hooks/use-async'
import { useAuth } from '@/lib/auth-context'
import { userApi } from '@/lib/endpoints'
import { ROLE_LABEL } from '@/lib/format'
import type { User, UserRole } from '@/lib/types'
import { Search } from '@/components/animate-ui/icons/search'
import { X } from '@/components/animate-ui/icons/x'
import { Plus } from '@/components/animate-ui/icons/plus'
import { Users } from '@/components/animate-ui/icons/users'
import { Lock } from '@/components/animate-ui/icons/lock'
import { LockKeyholeOpen } from '@/components/animate-ui/icons/lock-keyhole-open'
import { Trash2 } from '@/components/animate-ui/icons/trash-2'

const ROLES: UserRole[] = ['customer', 'owner', 'admin']

function CreateUserDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState<UserRole>('owner')
  const [password, setPassword] = useState('')

  const { run: create, isPending, error } = useMutation(() =>
    userApi.create({
      email,
      password,
      full_name: fullName,
      phone: phone.trim() || null,
      role,
    }),
  )

  function reset() {
    setEmail('')
    setFullName('')
    setPhone('')
    setRole('owner')
    setPassword('')
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const created = await create()
    if (!created) return
    toast.success(`${created.full_name} created`)
    setOpen(false)
    reset()
    onCreated()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) reset()
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus size={15} animateOnTap />
          Add user
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Provision a user</DialogTitle>
            <DialogDescription>
              Owner and admin accounts can only be created here, never through public signup.
            </DialogDescription>
          </DialogHeader>

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="new-full-name">Full name</FieldLabel>
              <Input
                id="new-full-name"
                required
                minLength={2}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="new-email">Email</FieldLabel>
              <Input
                id="new-email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="new-phone">Phone</FieldLabel>
              <Input
                id="new-phone"
                type="tel"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="Optional"
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="new-role">Role</FieldLabel>
              <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
                <SelectTrigger id="new-role" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((option) => (
                    <SelectItem key={option} value={option}>
                      {ROLE_LABEL[option]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel htmlFor="new-password">Temporary password</FieldLabel>
              <PasswordInput
                id="new-password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>

            {error ? <FieldError>{error.message}</FieldError> : null}
          </FieldGroup>

          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Creating…' : 'Create user'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function UserRow({
  user,
  isSelf,
  onToggleActive,
  onToggleVerified,
  onChangeRole,
  onDeactivate,
  isPending,
}: {
  user: User
  isSelf: boolean
  onToggleActive: () => void
  onToggleVerified: () => void
  onChangeRole: (role: UserRole) => void
  onDeactivate: () => void
  isPending: boolean
}) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{user.full_name}</span>
            <RoleBadge role={user.role} />
            {isSelf ? <span className="text-xs text-muted-foreground">(you)</span> : null}
          </div>
          <p className="truncate text-sm text-muted-foreground">{user.email}</p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Verified
            <Switch
              checked={user.is_verified}
              disabled={isPending}
              onCheckedChange={onToggleVerified}
              aria-label={`Toggle verification for ${user.email}`}
            />
          </label>

          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Active
            <Switch
              checked={user.is_active}
              // The API rejects self-demotion and self-deactivation, so the
              // control is disabled rather than letting it fail on submit.
              disabled={isPending || isSelf}
              onCheckedChange={onToggleActive}
              aria-label={`Toggle active for ${user.email}`}
            />
          </label>

          <Select
            value={user.role}
            onValueChange={(value) => onChangeRole(value as UserRole)}
            disabled={isPending || isSelf}
          >
            <SelectTrigger
              className="w-32"
              aria-label={`Change role for ${user.email}`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((option) => (
                <SelectItem key={option} value={option}>
                  {ROLE_LABEL[option]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {user.is_active && !isSelf ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  disabled={isPending}
                  aria-label={`Deactivate ${user.email}`}
                >
                  <Trash2 size={15} />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Deactivate {user.email}?</AlertDialogTitle>
                  <AlertDialogDescription>
                    They will be signed out everywhere and unable to sign back in. This revokes
                    every active session immediately.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={onDeactivate}>Deactivate</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : (
            <span className="inline-flex size-7 items-center justify-center text-muted-foreground/40">
              <LockKeyholeOpen size={15} />
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function AdminUsersPage() {
  const [searchInput, setSearchInput] = useState('')
  const search = useDebounced(searchInput.trim(), 300)

  const { data: users, error, isLoading, refetch } = useAsync(
    () => userApi.list({ search: search || undefined, limit: 100 }),
    [search],
  )

  const { run: update, isPending } = useMutation(
    (input: { id: number; payload: Parameters<typeof userApi.update>[1] }) =>
      userApi.update(input.id, input.payload),
  )

  const { run: deactivate } = useMutation((id: number) => userApi.deactivate(id))

  // The API refuses self-demotion and self-deactivation, so the row for the
  // signed-in admin has those controls disabled rather than letting them fail.
  const selfEmail = useAuth().user?.email

  async function apply(id: number, payload: Parameters<typeof userApi.update>[1], label: string) {
    const result = await update({ id, payload })
    if (!result) {
      toast.error('That change was rejected')
      return
    }
    toast.success(label)
    refetch()
  }

  async function handleDeactivate(user: User) {
    const result = await deactivate(user.id)
    if (!result) {
      toast.error('Could not deactivate that user')
      return
    }
    toast.success(`${user.email} deactivated`)
    refetch()
  }

  const list = users ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Provision accounts, change roles, and revoke access."
        actions={<CreateUserDialog onCreated={refetch} />}
      />

      <div className="relative max-w-sm">
        <Search
          size={16}
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search by email"
          aria-label="Search users by email"
          className="pr-9 pl-9"
        />
        {searchInput ? (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Clear search"
            className="absolute top-1/2 right-1.5 -translate-y-1/2"
            onClick={() => setSearchInput('')}
          >
            <X size={14} />
          </Button>
        ) : null}
      </div>

      {isLoading ? (
        <OrbPanel state="searching" label="Loading users" />
      ) : error ? (
        <ErrorState message={error.message} onRetry={refetch} />
      ) : list.length === 0 ? (
        <EmptyState
          orbState="shaping"
          title={search ? `No users matching “${search}”` : 'No users yet'}
          description={search ? 'Try a different email fragment.' : undefined}
          action={
            search ? (
              <Button variant="outline" onClick={() => setSearchInput('')}>
                Clear search
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {list.map((user) => (
            <UserRow
              key={user.id}
              user={user}
              isSelf={user.email === selfEmail}
              isPending={isPending}
              onToggleActive={() =>
                void apply(
                  user.id,
                  { is_active: !user.is_active },
                  user.is_active ? 'User deactivated' : 'User reactivated',
                )
              }
              onToggleVerified={() =>
                void apply(
                  user.id,
                  { is_verified: !user.is_verified },
                  user.is_verified ? 'Verification removed' : 'User verified',
                )
              }
              onChangeRole={(role) =>
                void apply(user.id, { role }, `Role changed to ${ROLE_LABEL[role]}`)
              }
              onDeactivate={() => void handleDeactivate(user)}
            />
          ))}
        </div>
      )}

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <Users size={13} />
        {list.length} user{list.length === 1 ? '' : 's'} shown
        <Lock size={13} />
        Deactivating a user revokes all of their sessions.
      </p>
    </div>
  )
}
