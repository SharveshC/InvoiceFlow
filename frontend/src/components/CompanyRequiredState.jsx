function CompanyRequiredState({ message, onNavigateToCreateCompany }) {
  return (
    <div className="card empty-state-box">
      <h4>Create a company first</h4>
      <p>{message}</p>
      <button
        type="button"
        className="btn-primary"
        onClick={onNavigateToCreateCompany}
      >
        Create Company
      </button>
    </div>
  );
}

export default CompanyRequiredState;

