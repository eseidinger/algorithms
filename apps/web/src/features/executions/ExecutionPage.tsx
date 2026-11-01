import {
  Alert,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router'
import {
  executionIdSchema,
  ExecutionNotFoundError,
  getExecution,
} from '../../api/executions'

export default function ExecutionPage() {
  const { executionId } = useParams()
  const id = executionIdSchema.safeParse(executionId)
  const execution = useQuery({
    queryKey: ['execution', executionId],
    queryFn: ({ signal }) => getExecution(executionId!, signal),
    enabled: id.success,
    retry: false,
    refetchInterval: (query) => {
      if (query.state.status === 'error') return false
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? 1000 : false
    },
  })

  if (!id.success) return <Alert severity="error">Invalid execution ID.</Alert>
  if (execution.isPending)
    return <CircularProgress aria-label="Loading execution" />
  if (execution.isError) {
    return (
      <Stack spacing={2}>
        <Alert severity="error">
          {execution.error instanceof ExecutionNotFoundError
            ? 'Execution not found.'
            : 'Could not load the execution.'}
        </Alert>
        <Button
          onClick={() => void execution.refetch()}
          disabled={execution.isFetching}
        >
          Retry
        </Button>
      </Stack>
    )
  }

  const data = execution.data
  return (
    <Stack spacing={2}>
      <Typography component="h1" variant="h4">
        Fibonacci execution
      </Typography>
      <Typography>Execution ID: {data.id}</Typography>
      <Typography>Status: {data.status}</Typography>
      <Typography>Input: n = {data.input.n}</Typography>
      {data.status === 'queued' && (
        <Alert severity="info">Waiting for a worker.</Alert>
      )}
      {data.status === 'running' && (
        <Alert severity="info">Calculation running.</Alert>
      )}
      {data.status === 'cancelled' && (
        <Alert severity="info">Execution cancelled.</Alert>
      )}
      {data.status === 'failed' && (
        <Alert severity="error">Execution failed.</Alert>
      )}
      {data.status === 'succeeded' && (
        <Alert severity="success">Result: {data.result!.value}</Alert>
      )}
      {data.durationMs !== null && (
        <Typography>Duration: {data.durationMs} ms</Typography>
      )}
    </Stack>
  )
}
