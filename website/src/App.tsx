import './App.css';
import Dashboard from './components/Dashboard';

/**
 * Main App Component
 * 
 * The dashboard automatically fetches and displays graphs from the database.
 * New graphs can be added without recompiling - just add data to the 
 * backend via the /aggregator endpoint and it will appear automatically.
 */
function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;
