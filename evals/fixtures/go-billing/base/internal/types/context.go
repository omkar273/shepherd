package types

import "context"

type ctxKey string

const (
	tenantKey      ctxKey = "tenant_id"
	environmentKey ctxKey = "environment_id"
)

func WithScope(ctx context.Context, tenantID, environmentID string) context.Context {
	ctx = context.WithValue(ctx, tenantKey, tenantID)
	return context.WithValue(ctx, environmentKey, environmentID)
}

func TenantID(ctx context.Context) string {
	v, _ := ctx.Value(tenantKey).(string)
	return v
}

func EnvironmentID(ctx context.Context) string {
	v, _ := ctx.Value(environmentKey).(string)
	return v
}
