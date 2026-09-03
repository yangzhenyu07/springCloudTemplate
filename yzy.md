# Project Constraint Document

## Project Information
- **Project Name**: java-20260603
- **GroupId**: com.example
- **Version**: 1.0-SNAPSHOT
- **Java Version**: 17
- **Build Tool**: Maven

## Module Structure
- yzy-demo
- redis-module
- common-module-v1
- common-module-v2

## Tech Stack
- 无额外依赖 (from parent POM)

## Code Conventions

### Naming Conventions
- **Class Name**: PascalCase (e.g., `UserService`, `OrderController`)
- **Method Name**: camelCase (e.g., `getUserById`, `createOrder`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`)
- **Package Name**: lowercase (e.g., `com.example.service`)
- **Variable Name**: camelCase (e.g., `userRepository`, `orderList`)

### Code Style
- **Indentation**: 4 spaces (no tabs)
- **Line Length**: max 120 characters
- **Import Order**: 
  1. java.*
  2. javax.*
  3. org.*
  4. com.*
  5. Third-party libraries
- **Blank Lines**: between methods, between logical blocks

### Comment Conventions
- **Class Comment**: Required, describe class purpose
- **Method Comment**: Required, describe functionality, parameters, return values
- **Complex Logic**: Required, describe algorithm approach
- **TODO**: Use `// TODO: description` format

## Development Constraints

### Code Quality
1. **Single Responsibility**: Each class does one thing
2. **Method Length**: max 50 lines
3. **Class Length**: max 500 lines
4. **Nesting Level**: max 3 levels

### Dependency Management
1. **Version Control**: Managed by parent POM
2. **New Dependencies**: Evaluate necessity and impact
3. **Remove Dependencies**: Confirm no other modules use it

### Modularization
1. **Module Responsibility**: Clear boundaries for each module
2. **Dependency Direction**: Avoid circular dependencies
3. **Common Code**: Place in common-module

### Security Conventions
1. **Sensitive Information**: No hardcoding, use configuration
2. **Input Validation**: All external inputs must be validated
3. **Logging**: Do not log sensitive information

## AI Behavior Guidelines

### Code Generation
- Strictly follow the above naming and code conventions
- Prefer using existing dependencies and utility classes
- Consider modularization and extensibility for new features
- Check for similar implementations before generating code

### Code Modification
- Maintain existing code style
- Do not change existing API signatures
- New features should not break existing tests
- Important modifications require user confirmation

### Dependency Management
- Check for similar functionality before adding new dependencies
- Evaluate license compatibility
- Consider maintenance status and community activity

### Architecture Decisions
- Follow existing project architecture patterns
- Major architecture changes require user confirmation
- Maintain backward compatibility

## Version History
- **1.0** (Initial version): Basic project constraints
