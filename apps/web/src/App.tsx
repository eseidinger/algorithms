import { AppBar, Container, Toolbar, Typography } from '@mui/material'

export default function App() {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div">
            Algorithm Lab
          </Typography>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Algorithm Catalog
        </Typography>

        <Typography>
          Explore algorithms, run experiments and compare results.
        </Typography>
      </Container>
    </>
  )
}
