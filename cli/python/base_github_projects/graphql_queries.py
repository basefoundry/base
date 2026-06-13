FETCH_PROJECT_FIELDS = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          __typename
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options { id name color description }
          }
        }
      }
    }
  }
}
"""

FETCH_PROJECT_VIEWS = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      views(first: 20) {
        nodes { name layout }
      }
    }
  }
}
"""

CREATE_PROJECT = """
mutation($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 { id title }
  }
}
"""

COPY_PROJECT = """
mutation($projectId: ID!, $ownerId: ID!, $title: String!) {
  copyProjectV2(input: {projectId: $projectId, ownerId: $ownerId, title: $title, includeDraftIssues: false}) {
    projectV2 { id title }
  }
}
"""

FETCH_REPOSITORY_ID = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) { id }
}
"""

LINK_PROJECT_TO_REPOSITORY = """
mutation($projectId: ID!, $repositoryId: ID!) {
  linkProjectV2ToRepository(input: {projectId: $projectId, repositoryId: $repositoryId}) {
    repository { id }
  }
}
"""

FETCH_PROJECT_REPOSITORY_NAMES = """
query($projectId: ID!, $cursor: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      repositories(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { nameWithOwner }
      }
    }
  }
}
"""

CREATE_SINGLE_SELECT_FIELD = """
mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  createProjectV2Field(input: {
    projectId: $projectId,
    dataType: SINGLE_SELECT,
    name: $name,
    singleSelectOptions: $options
  }) {
    projectV2Field { ... on ProjectV2SingleSelectField { id name } }
  }
}
"""

UPDATE_SINGLE_SELECT_FIELD = """
mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  updateProjectV2Field(input: {
    fieldId: $fieldId,
    singleSelectOptions: $options
  }) {
    projectV2Field { ... on ProjectV2SingleSelectField { id name } }
  }
}
"""

FETCH_ISSUE_ID = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) { id }
  }
}
"""

FETCH_REPOSITORY_ISSUE_IDS = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $cursor, states: [OPEN, CLOSED], orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes { id }
    }
  }
}
"""

FETCH_PROJECT_ISSUE_CONTENT_IDS = """
query($projectId: ID!, $cursor: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          content { ... on Issue { id } }
        }
      }
    }
  }
}
"""

FETCH_PROJECT_ISSUE_ITEMS_WITH_FIELDS = """
query($projectId: ID!, $cursor: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            ... on Issue {
              id
              number
              title
            }
          }
          fieldValues(first: 50) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2SingleSelectField { name } }
              }
            }
          }
        }
      }
    }
  }
}
"""

FIND_PROJECT_ITEM_ID = """
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { id } }
        }
      }
    }
  }
}
"""

ADD_PROJECT_ITEM = """
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}
"""

UPDATE_ITEM_FIELD = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId,
    itemId: $itemId,
    fieldId: $fieldId,
    value: {singleSelectOptionId: $optionId}
  }) {
    projectV2Item { id }
  }
}
"""
